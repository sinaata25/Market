"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/client-api";

type Me = {
  id: number;
  phone: string;
  name: string | null;
  isStaff?: boolean;
} | null;

export default function HeaderActions() {
  const router = useRouter();
  const [user, setUser] = useState<Me>(null);
  const [count, setCount] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  const refreshCart = useCallback(() => {
    fetch("/api/cart")
      .then((r) => r.json())
      .then((json) => {
        if (json.ok) setCount(json.data.cart.itemsCount);
      })
      .catch(() => {
        // بی‌صدا — شمارنده صفر می‌ماند
      });
  }, []);

  useEffect(() => {
    fetch("/api/auth/me")
      .then((r) => r.json())
      .then((json) => {
        if (json.ok) setUser(json.data.user);
      })
      .catch(() => {});
    refreshCart();

    // با افزودن کالا از هر جای سایت، شمارنده به‌روز شود
    const onUpdate = () => refreshCart();
    window.addEventListener("cart:updated", onUpdate);
    return () => window.removeEventListener("cart:updated", onUpdate);
  }, [refreshCart]);

  async function logout() {
    await api.post("/api/auth/logout");
    setUser(null);
    setMenuOpen(false);
    router.refresh();
    refreshCart();
  }

  return (
    <div className="flex shrink-0 items-center gap-2">
      {user ? (
        <div
          className="relative"
          onMouseEnter={() => setMenuOpen(true)}
          onMouseLeave={() => setMenuOpen(false)}
        >
          <button className="flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-400">
            <span>👤</span>
            <span dir="ltr" className="font-num">
              {user.name ?? user.phone}
            </span>
            <span className="text-xs">▾</span>
          </button>
          {menuOpen && (
            <div className="absolute left-0 top-full z-50 pt-2">
              <div className="w-48 overflow-hidden rounded-xl border border-slate-100 bg-white py-1 shadow-lg">
                {[
                  { href: "/profile", icon: "👤", label: "پروفایل من" },
                  { href: "/profile/orders", icon: "📦", label: "سفارش‌های من" },
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
                {user.isStaff && (
                  <Link
                    href="/admin"
                    className="block border-t border-slate-100 px-4 py-2.5 text-sm text-violet-600 transition hover:bg-violet-50"
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
          href="/login"
          className="hidden items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-400 hover:text-brand-700 sm:flex"
        >
          <span>👤</span>
          <span>ورود | ثبت‌نام</span>
        </Link>
      )}

      <Link
        href="/cart"
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
