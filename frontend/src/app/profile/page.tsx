"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { formatPrice } from "@/lib/products";
import { faNum, StatusBadge, faDate } from "@/components/admin/ui";

type Profile = {
  user: {
    id: number;
    phone: string;
    name: string | null;
    dateJoined: string;
  };
  stats: {
    ordersCount: number;
    pendingCount: number;
    deliveredCount: number;
    totalSpent: number;
    addressesCount: number;
    favoritesCount: number;
    commentsCount: number;
    ratingsCount: number;
  };
};

type Order = {
  id: number;
  code: string;
  status: string;
  createdAt: string;
  totalPrice: number;
  items: { id: number; title: string; qty: number }[];
};

export default function ProfileHome() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    api.get<Profile>("/api/auth/profile").then((res) => {
      if (res.ok && res.data) setProfile(res.data);
    });
    api.get<{ orders: Order[] }>("/api/orders").then((res) => {
      if (res.ok && res.data) setOrders(res.data.orders.slice(0, 3));
    });
  }, []);

  if (!profile) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  const { stats, user } = profile;

  return (
    <div className="space-y-5">
      {/* خوش‌آمدگویی */}
      <section className="overflow-hidden rounded-3xl bg-gradient-to-l from-brand-700 to-brand-500 px-6 py-6 text-white">
        <h1 className="text-lg font-bold">
          سلام {user.name ?? "دوست عزیز"} 👋
        </h1>
        <p className="mt-1 text-xs text-brand-50 font-num">
          عضو گروه صنعتی توانا از {faDate(user.dateJoined)}
        </p>
      </section>

      {/* آمار */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MiniStat
          icon="📦"
          value={faNum(stats.ordersCount)}
          label="سفارش ثبت‌شده"
          href="/profile/orders"
        />
        <MiniStat
          icon="⏳"
          value={faNum(stats.pendingCount)}
          label="در انتظار پرداخت"
          href="/profile/orders"
          highlight={stats.pendingCount > 0}
        />
        <MiniStat
          icon="❤️"
          value={faNum(stats.favoritesCount)}
          label="علاقه‌مندی"
          href="/profile/favorites"
        />
        <MiniStat
          icon="📍"
          value={faNum(stats.addressesCount)}
          label="آدرس ذخیره‌شده"
          href="/profile/addresses"
        />
      </div>

      {/* مجموع خرید */}
      <div className="flex items-center justify-between rounded-2xl border border-slate-100 bg-white p-5">
        <div>
          <p className="text-xs text-slate-400">مجموع خریدهای شما</p>
          <p className="mt-1 text-xl font-bold text-slate-800 font-num">
            {formatPrice(stats.totalSpent)}
            <span className="mr-1 text-xs font-normal text-slate-400">
              تومان
            </span>
          </p>
        </div>
        <div className="text-left">
          <p className="text-xs text-slate-400">سفارش تحویل‌شده</p>
          <p className="mt-1 text-xl font-bold text-emerald-600 font-num">
            {faNum(stats.deliveredCount)}
          </p>
        </div>
      </div>

      {/* آخرین سفارش‌ها */}
      <section className="overflow-hidden rounded-2xl border border-slate-100 bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-bold text-slate-700">آخرین سفارش‌ها</h2>
          <Link
            href="/profile/orders"
            className="text-xs text-brand-600 hover:underline"
          >
            مشاهده همه ←
          </Link>
        </div>
        {orders.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <span className="mb-3 block text-4xl">🛒</span>
            <p className="mb-4 text-sm text-slate-500">
              هنوز سفارشی ثبت نکرده‌اید
            </p>
            <Link
              href="/"
              className="inline-block rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white"
            >
              شروع خرید
            </Link>
          </div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {orders.map((o) => (
              <li key={o.id}>
                <Link
                  href={`/profile/orders/${o.id}`}
                  className="flex items-center gap-3 px-5 py-4 transition hover:bg-slate-50/60"
                >
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <code
                        dir="ltr"
                        className="text-xs text-slate-500 font-num"
                      >
                        {o.code}
                      </code>
                      <StatusBadge status={o.status} />
                    </div>
                    <p className="truncate text-xs text-slate-400">
                      {o.items.map((i) => i.title).join("، ")}
                    </p>
                  </div>
                  <span className="shrink-0 text-sm font-bold text-slate-700 font-num">
                    {formatPrice(o.totalPrice)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function MiniStat({
  icon,
  value,
  label,
  href,
  highlight = false,
}: {
  icon: string;
  value: string;
  label: string;
  href: string;
  highlight?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`rounded-2xl border bg-white p-4 text-center transition hover:shadow-sm ${
        highlight
          ? "border-amber-200 bg-amber-50/40"
          : "border-slate-100 hover:border-brand-200"
      }`}
    >
      <span className="mb-1 block text-2xl">{icon}</span>
      <p className="text-lg font-bold text-slate-800 font-num">{value}</p>
      <p className="text-[11px] text-slate-400">{label}</p>
    </Link>
  );
}
