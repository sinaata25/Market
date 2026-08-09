"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, notifyAuthChanged, subscribeAuthChanged } from "@/lib/client-api";

type Me = {
  id: number;
  phone: string;
  name: string | null;
  isStaff?: boolean;
  isSeoManager?: boolean;
} | null;

export default function HeaderActions() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<Me>(null);
  const [count, setCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const userRequest = useRef(0);
  const cartRequest = useRef(0);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);

  const refreshCart = useCallback(() => {
    const requestId = ++cartRequest.current;
    fetch("/api/cart", { cache: "no-store" })
      .then((r) => r.json())
      .then((json) => {
        if (requestId === cartRequest.current && json.ok) {
          setCount(json.data.cart.itemsCount);
        }
      })
      .catch(() => {
        // بی‌صدا — شمارنده صفر می‌ماند
      });
  }, []);

  const refreshUser = useCallback(() => {
    const requestId = ++userRequest.current;
    api.get<{ user: Me }>("/api/auth/me").then((response) => {
      if (requestId === userRequest.current && response.ok) {
        setUser(response.data?.user ?? null);
      }
    });
  }, []);

  useEffect(() => {
    refreshUser();
    refreshCart();

    // با تغییر سبد یا session در هر تب، header همگام می‌ماند.
    const onUpdate = () => refreshCart();
    const onAuthChanged = () => {
      refreshUser();
      refreshCart();
    };
    const onFocus = () => {
      refreshUser();
      refreshCart();
    };
    window.addEventListener("cart:updated", onUpdate);
    window.addEventListener("focus", onFocus);
    const unsubscribeAuth = subscribeAuthChanged(onAuthChanged);
    return () => {
      userRequest.current += 1;
      cartRequest.current += 1;
      window.removeEventListener("cart:updated", onUpdate);
      window.removeEventListener("focus", onFocus);
      unsubscribeAuth();
    };
  }, [refreshCart, refreshUser]);

  async function logout() {
    const response = await api.post("/api/auth/logout");
    if (!response.ok) return;
    setUser(null);
    setMenuOpen(false);
    notifyAuthChanged();
    router.replace("/");
  }

  return (
    <div className="flex shrink-0 items-center gap-2">
      {user ? (
        <div
          className="relative"
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget)) {
              setMenuOpen(false);
            }
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setMenuOpen(false);
              menuButtonRef.current?.focus();
            }
          }}
        >
          <button
            ref={menuButtonRef}
            type="button"
            aria-expanded={menuOpen}
            aria-controls="account-menu"
            onClick={() => setMenuOpen((open) => !open)}
            className="flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-400"
          >
            <span>👤</span>
            <span dir="ltr" className="font-num">
              {user.name ?? user.phone}
            </span>
            <span className="text-xs">▾</span>
          </button>
          {menuOpen && (
            <div
              id="account-menu"
              className="absolute left-0 top-full z-50 pt-2"
            >
              <div className="w-48 overflow-hidden rounded-xl border border-slate-100 bg-white py-1 shadow-lg">
                {[
                  { href: "/profile", icon: "👤", label: "پروفایل من" },
                  {
                    href: "/profile/orders",
                    icon: "📦",
                    label: "سفارش‌های من",
                  },
                  {
                    href: "/profile/addresses",
                    icon: "📍",
                    label: "آدرس‌های من",
                  },
                  {
                    href: "/profile/favorites",
                    icon: "❤️",
                    label: "علاقه‌مندی‌ها",
                  },
                ].map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="block px-4 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50"
                    onClick={() => setMenuOpen(false)}
                  >
                    {item.icon} {item.label}
                  </Link>
                ))}
                {(user.isStaff || user.isSeoManager) && (
                  <Link
                    href="/admin"
                    className="block px-4 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50"
                    onClick={() => setMenuOpen(false)}
                  >
                    🎛️ پنل مدیریت
                  </Link>
                )}
                <button
                  onClick={logout}
                  className="block w-full border-t border-slate-100 px-4 py-2.5 text-right text-sm text-red-500 transition hover:bg-red-50"
                >
                  ⏻ خروج از حساب
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <Link
          href={
            pathname === "/login"
              ? "/login"
              : `/login?next=${encodeURIComponent(pathname)}`
          }
          className="hidden items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-400 hover:text-brand-700 sm:flex"
        >
          <span>👤</span>
          <span>ورود | ثبت‌نام</span>
        </Link>
      )}

      {user?.isStaff && (
        <Link
          href="/admin"
          aria-label="داشبورد مدیریت"
          title="داشبورد مدیریت"
          className="block px-4 py-2.5 text-sm text-slate-600 transition hover:bg-slate-50"
        >
          <span aria-hidden="true">🎛️</span>
          <span className="hidden sm:inline">داشبورد مدیریت</span>
        </Link>
      )}

      <Link
        href="/cart"
        aria-label="سبد خرید"
        className="relative grid h-11 w-11 place-items-center rounded-xl border border-slate-200 text-xl transition hover:border-brand-400"
      >
        🛒
        <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-brand-600 px-1 text-[11px] font-bold text-white font-num">
          {count.toLocaleString("fa-IR")}
        </span>
      </Link>
    </div>
  );
}
