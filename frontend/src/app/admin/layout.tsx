"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  api,
  notifyAuthChanged,
  subscribeAuthChanged,
} from "@/lib/client-api";

type Me = {
  id: number;
  phone: string;
  name: string | null;
  isStaff?: boolean;
  isSeoManager?: boolean;
} | null;

// منوی مدیران فروشگاه (staff)
const SHOP_NAV = [
  { href: "/admin", icon: "📊", label: "داشبورد" },
  { href: "/admin/orders", icon: "📦", label: "سفارش‌ها" },
  { href: "/admin/products", icon: "🛠️", label: "محصولات" },
  {
    href: "/admin/specifications",
    icon: "📋",
    label: "مشخصات محصولات",
  },
  { href: "/admin/categories", icon: "🗂️", label: "دسته‌بندی‌ها" },
  { href: "/admin/brands", icon: "🏷️", label: "برندها" },
  { href: "/admin/users", icon: "👥", label: "کاربران" },
  { href: "/admin/comments", icon: "💬", label: "دیدگاه‌ها و پرسش‌ها" },
  { href: "/admin/blog", icon: "📝", label: "وبلاگ" },
  { href: "/admin/homepage", icon: "🏠", label: "صفحه اصلی" },
  { href: "/admin/content", icon: "📄", label: "محتوای صفحات" },
];

// منوی سئو (staff و مدیر سئو)
const SEO_NAV = [
  { href: "/admin/seo", icon: "🎯", label: "نمای کلی سئو" },
  { href: "/admin/seo/pages", icon: "📝", label: "متای صفحات" },
  { href: "/admin/seo/redirects", icon: "↪️", label: "ریدایرکت‌ها" },
  { href: "/admin/seo/404s", icon: "🚫", label: "خطاهای ۴۰۴" },
  { href: "/admin/seo/images", icon: "🖼️", label: "Alt تصاویر" },
  { href: "/admin/seo/reports", icon: "⚡", label: "سرعت و لینک‌ها" },
  { href: "/admin/seo/settings", icon: "⚙️", label: "تنظیمات سئو" },
];

export default function AdminLayout({
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

  // در حال بررسی دسترسی
  if (!checked) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-slate-400">
        در حال بررسی دسترسی...
      </div>
    );
  }

  // لاگین نیست
  if (!me) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <span className="mb-4 block text-5xl">🔐</span>
        <h1 className="mb-2 text-lg font-bold text-slate-800">
          ورود به داشبورد مدیریت
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          برای دسترسی به داشبورد ابتدا وارد حساب خود شوید.
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

  // نه staff است نه مدیر سئو
  if (!me.isStaff && !me.isSeoManager) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center">
        <span className="mb-4 block text-5xl">⛔</span>
        <h1 className="mb-2 text-lg font-bold text-slate-800">
          دسترسی مدیریتی ندارید
        </h1>
        <p className="mb-6 text-sm leading-7 text-slate-500">
          حساب <b className="font-num">{me.phone}</b> مدیر نیست. برای دریافت
          دسترسی، این دستور را در بک‌اند اجرا کنید:
        </p>
        <code
          dir="ltr"
          className="mb-6 block rounded-xl bg-slate-800 px-4 py-3 text-xs text-emerald-300"
        >
          python manage.py make_admin {me.phone}
        </code>
        <Link href="/" className="text-sm text-brand-600 hover:underline">
          بازگشت به فروشگاه ←
        </Link>
      </div>
    );
  }

  // مدیر سئو فقط بخش سئو را می‌بیند؛ staff همه را
  const showShopNav = Boolean(me.isStaff);
  const seoOnlyBlocked =
    !me.isStaff && me.isSeoManager && !pathname.startsWith("/admin/seo");

  return (
    <div className="site-shell flex flex-col gap-5 py-4 sm:py-6 lg:flex-row">
      {/* سایدبار */}
      <aside className="min-w-0 lg:w-56 lg:shrink-0">
        <div className="overflow-hidden rounded-2xl bg-secondary-900 text-secondary-200 lg:sticky-below-header">
          <div className="border-b border-secondary-700/60 px-5 py-4">
            <p className="text-sm font-bold text-white">پنل مدیریت</p>
            <p className="mt-1 text-[11px] text-slate-400 font-num" dir="ltr">
              {me.name ?? me.phone}
            </p>
          </div>
          <nav
            aria-label="منوی مدیریت"
            className="grid grid-cols-2 gap-1 p-2 sm:grid-cols-3 lg:block"
          >
            {showShopNav &&
              SHOP_NAV.map((item) => {
                const active =
                  item.href === "/admin"
                    ? pathname === "/admin"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex min-h-11 min-w-0 items-center gap-2 rounded-xl px-3 py-2.5 text-sm leading-5 transition lg:mb-1 lg:gap-3 lg:whitespace-nowrap lg:px-4 ${
                      active
                        ? "bg-brand-600 font-medium text-white"
                        : "hover:bg-secondary-800 hover:text-white"
                    }`}
                  >
                    <span className="shrink-0">{item.icon}</span>
                    {item.label}
                  </Link>
                );
              })}

            <p className="hidden lg:mb-1 lg:mt-3 lg:block lg:px-4 lg:text-[10px] lg:font-bold lg:tracking-wide lg:text-slate-500">
              سئو
            </p>
            {SEO_NAV.map((item) => {
              const active =
                item.href === "/admin/seo"
                  ? pathname === "/admin/seo"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex min-h-11 min-w-0 items-center gap-2 rounded-xl px-3 py-2.5 text-sm leading-5 transition lg:mb-1 lg:gap-3 lg:whitespace-nowrap lg:px-4 ${
                    active
                      ? "bg-brand-600 font-medium text-white"
                    : "hover:bg-secondary-800 hover:text-white"
                  }`}
                >
                  <span className="shrink-0">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex gap-1 border-t border-secondary-700/60 p-2 lg:block">
            <Link
              href="/"
              className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm transition hover:bg-secondary-800 hover:text-white lg:justify-start lg:gap-3 lg:px-4"
            >
              <span>🏬</span> مشاهده فروشگاه
            </Link>
            <button
              onClick={logout}
              data-admin-navigation
              className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-right text-sm text-red-400 transition hover:bg-secondary-800 lg:w-full lg:justify-start lg:gap-3 lg:px-4"
            >
              <span>⏻</span> خروج
            </button>
          </div>
        </div>
      </aside>

      {/* محتوا — مدیر سئو به بخش‌های فروشگاهی دسترسی ندارد */}
      <main className="min-w-0 flex-1">
        {seoOnlyBlocked ? (
          <div className="rounded-2xl border border-amber-100 bg-amber-50 p-6 text-center sm:p-8">
            <span className="mb-3 block text-4xl">🔒</span>
            <p className="mb-4 text-sm text-slate-600">
              نقش شما «مدیر سئو» است و به این بخش دسترسی ندارید.
            </p>
            <Link
              href="/admin/seo"
              className="inline-block rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white"
            >
              رفتن به پنل سئو
            </Link>
          </div>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
