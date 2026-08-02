"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/client-api";

type Me = {
  id: number;
  phone: string;
  name: string | null;
  isStaff?: boolean;
} | null;

const NAV = [
  { href: "/profile", icon: "👤", label: "خلاصه حساب" },
  { href: "/profile/orders", icon: "📦", label: "سفارش‌های من" },
  { href: "/profile/addresses", icon: "📍", label: "آدرس‌های من" },
  { href: "/profile/favorites", icon: "❤️", label: "علاقه‌مندی‌ها" },
  { href: "/profile/reviews", icon: "💬", label: "دیدگاه‌های من" },
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

  useEffect(() => {
    api.get<{ user: Me }>("/api/auth/me").then((res) => {
      if (res.ok) setMe(res.data?.user ?? null);
      setChecked(true);
    });
  }, []);

  async function logout() {
    await api.post("/api/auth/logout");
    window.dispatchEvent(new CustomEvent("cart:updated"));
    router.push("/");
    router.refresh();
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
          href="/login"
          className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          ورود | ثبت‌نام
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="flex flex-col gap-5 lg:flex-row">
        {/* سایدبار */}
        <aside className="lg:w-64 lg:shrink-0">
          <div className="lg:sticky lg:top-24">
            {/* کارت کاربر */}
            <div className="mb-3 rounded-2xl border border-slate-100 bg-white p-5 text-center">
              <span className="mx-auto mb-3 grid h-16 w-16 place-items-center rounded-full bg-brand-50 text-3xl">
                👤
              </span>
              <p className="text-sm font-bold text-slate-800">
                {me.name ?? "کاربر توانا"}
              </p>
              <p className="mt-1 text-xs text-slate-400 font-num" dir="ltr">
                {me.phone}
              </p>
            </div>

            {/* منو */}
            <nav className="overflow-hidden rounded-2xl border border-slate-100 bg-white p-2">
              {NAV.map((item) => {
                const active =
                  item.href === "/profile"
                    ? pathname === "/profile"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`mb-1 flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm transition ${
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

              {me.isStaff && (
                <Link
                  href="/admin"
                  className="mb-1 flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm text-violet-600 transition hover:bg-violet-50"
                >
                  <span>🎛️</span> پنل مدیریت
                </Link>
              )}

              <button
                onClick={logout}
                className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-right text-sm text-red-500 transition hover:bg-red-50"
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
