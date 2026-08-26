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

const NAV = [
  { href: "/profile", icon: "👤", label: "خلاصه حساب" },
  { href: "/profile/orders", icon: "📦", label: "سفارش‌های من" },
  { href: "/profile/addresses", icon: "📍", label: "آدرس‌های من" },
  { href: "/profile/favorites", icon: "❤️", label: "علاقه‌مندی‌ها" },
  { href: "/profile/comments", icon: "💬", label: "دیدگاه‌های من" },
  { href: "/profile/info", icon: "⚙️", label: "اطلاعات حساب" },
];

export default function ProfileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me>(null);
  const [checked, setChecked] = useState(false);
  const meRequest = useRef(0);

  const refreshMe = useCallback(() => {
    const requestId = ++meRequest.current;
    api.get<{ user: Me }>("/api/auth/me").then((res) => {
      if (requestId !== meRequest.current) return;
      if (res.ok) setMe(res.data?.user ?? null);
      setChecked(true);
    });
  }, []);

  useEffect(() => {
    refreshMe();
    const onFocus = () => refreshMe();
    window.addEventListener("focus", onFocus);
    const unsubscribeAuth = subscribeAuthChanged(refreshMe);
    return () => {
      meRequest.current += 1;
      window.removeEventListener("focus", onFocus);
      unsubscribeAuth();
    };
  }, [refreshMe]);

  async function logout() {
    const response = await api.post("/api/auth/logout");
    if (!response.ok) return;
    notifyAuthChanged();
    router.replace("/");
  }

  if (!checked) {
    return (
      <div className="grid min-h-[50vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  if (!me) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <span className="mb-4 block text-5xl">🔐</span>
        <h1 className="mb-2 text-lg font-bold text-slate-800">
          ورود به حساب کاربری
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          برای مشاهده پروفایل ابتدا وارد حساب خود شوید.
        </p>
        <Link
          href={`/login?next=${encodeURIComponent(pathname)}`}
          className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          ورود | ثبت‌نام
        </Link>
      </div>
    );
  }

  return (
    <div className="site-shell py-6">
      <div className="flex flex-col gap-5 lg:flex-row">
        {/* سایدبار */}
        <aside className="min-w-0 lg:w-64 lg:shrink-0">
          <div className="lg:sticky-below-header">
            {/* کارت کاربر */}
            <div className="mb-3 flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3 text-right lg:block lg:p-5 lg:text-center">
              <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand-50 text-2xl lg:mx-auto lg:mb-3 lg:h-16 lg:w-16 lg:text-3xl">
                👤
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-slate-800">
                  {me.name ?? "کاربر توانا"}
                </p>
                <p className="mt-1 text-xs text-slate-400 font-num" dir="ltr">
                  {me.phone}
                </p>
              </div>
            </div>

            {/* منو */}
            <nav aria-label="منوی حساب کاربری" className="responsive-scroll flex gap-1 rounded-2xl border border-slate-100 bg-white p-2 lg:block">
              {NAV.map((item) => {
                const active =
                  item.href === "/profile"
                    ? pathname === "/profile"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm transition lg:mb-1 lg:gap-3 lg:px-4 ${
                      active
                        ? "bg-brand-50 font-medium text-brand-700"
                        : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <span>{item.icon}</span>
                    {item.label}
                  </Link>
                );
              })}

              {(me.isStaff || me.isSeoManager) && (
                <Link
                  href="/admin"
                  className="flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2.5 text-right text-sm text-slate-600 transition hover:bg-blue-50 lg:w-full lg:gap-3 lg:px-4"
                >
                  <span>🎛️</span> پنل مدیریت
                </Link>
              )}

              <button
                onClick={logout}
                className="flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-3 py-2.5 text-right text-sm text-red-500 transition hover:bg-red-50 lg:w-full lg:gap-3 lg:px-4"
              >
                <span>⏻</span> خروج از حساب
              </button>
            </nav>
          </div>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
