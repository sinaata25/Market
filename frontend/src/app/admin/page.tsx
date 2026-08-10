"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { formatPrice } from "@/lib/products";
import {
  StatCard,
  StatusBadge,
  STATUS_FA,
  faNum,
  faDate,
  faDateTime,
} from "@/components/admin/ui";

type Stats = {
  totals: {
    revenue: number;
    orders: number;
    pendingOrders: number;
    users: number;
    products: number;
    comments: number;
    ratings: number;
    avgRating: number;
  };
  salesByDay: { date: string; total: number; count: number }[];
  statusBreakdown: Record<string, number>;
  topProducts: { product_id: number; title: string; qty: number; revenue: number }[];
  lowStock: { id: number; title: string; stock: number }[];
  recentOrders: {
    id: number;
    code: string;
    status: string;
    createdAt: string;
    fullName: string;
    totalPrice: number;
  }[];
};

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Stats>("/api/admin/stats").then((res) => {
      if (res.ok && res.data) setStats(res.data);
      else setError(res.error ?? "خطا در دریافت آمار");
    });
  }, []);

  if (error) {
    return (
      <div className="rounded-2xl border border-red-100 bg-red-50 p-6 text-center text-sm text-red-500">
        {error}
      </div>
    );
  }
  if (!stats) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری آمار...
      </div>
    );
  }

  const { totals } = stats;
  const maxDay = Math.max(...stats.salesByDay.map((d) => d.total), 1);

  return (
    <div className="space-y-5">
      <h1 className="text-lg font-bold text-slate-800">داشبورد</h1>

      {/* KPI ها */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          icon="💰"
          label="درآمد کل"
          value={`${formatPrice(totals.revenue)} تومان`}
          accent="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          icon="📦"
          label="سفارش‌ها"
          value={faNum(totals.orders)}
          sub={`${faNum(totals.pendingOrders)} در انتظار پرداخت`}
          accent="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon="👥"
          label="کاربران"
          value={faNum(totals.users)}
          accent="bg-violet-50 text-violet-600"
        />
        <StatCard
          icon="🛠️"
          label="محصولات"
          value={faNum(totals.products)}
          sub={`${faNum(totals.comments)} پیام — ${faNum(totals.ratings)} امتیاز — میانگین ${faNum(totals.avgRating)}★`}
          accent="bg-amber-50 text-amber-600"
        />
      </div>

      {/* نمودار فروش + وضعیت سفارش‌ها */}
      <div className="grid gap-5 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-100 bg-white p-5 lg:col-span-2">
          <h2 className="mb-4 text-sm font-bold text-slate-700">
            فروش ۱۴ روز اخیر
          </h2>
          <div className="flex h-44 items-end gap-1.5" dir="ltr">
            {stats.salesByDay.map((d) => (
              <div
                key={d.date}
                className="group relative flex h-full flex-1 flex-col justify-end"
              >
                <div
                  className={`rounded-t-md transition ${
                    d.total > 0
                      ? "bg-brand-500 group-hover:bg-brand-600"
                      : "bg-slate-100"
                  }`}
                  style={{
                    height: `${Math.max((d.total / maxDay) * 100, d.total > 0 ? 6 : 3)}%`,
                  }}
                />
                {/* تولتیپ */}
                <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg bg-slate-800 px-3 py-2 text-[11px] text-white group-hover:block">
                  <span className="font-num" dir="rtl">
                    {faDate(d.date)} — {formatPrice(d.total)} تومان (
                    {faNum(d.count)} سفارش)
                  </span>
                </div>
              </div>
            ))}
          </div>
          <div
            className="mt-2 flex justify-between text-[10px] text-slate-400 font-num"
            dir="ltr"
          >
            <span>{faDate(stats.salesByDay[0].date)}</span>
            <span>{faDate(stats.salesByDay[13].date)}</span>
          </div>
        </div>

        {/* وضعیت سفارش‌ها */}
        <div className="rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="mb-4 text-sm font-bold text-slate-700">
            وضعیت سفارش‌ها
          </h2>
          <ul className="space-y-3">
            {Object.entries(STATUS_FA).map(([key, s]) => {
              const count = stats.statusBreakdown[key] ?? 0;
              const pct = totals.orders ? (count / totals.orders) * 100 : 0;
              return (
                <li key={key}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-slate-600">{s.label}</span>
                    <span className="font-num text-slate-400">
                      {faNum(count)}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-brand-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      {/* سفارش‌های اخیر + هشدار موجودی + پرفروش‌ها */}
      <div className="grid gap-5 lg:grid-cols-3">
        {/* سفارش‌های اخیر */}
        <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h2 className="text-sm font-bold text-slate-700">سفارش‌های اخیر</h2>
            <Link
              href="/admin/orders"
              className="text-xs text-brand-600 hover:underline"
            >
              مشاهده همه ←
            </Link>
          </div>
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-50">
              {stats.recentOrders.length === 0 && (
                <tr>
                  <td className="px-5 py-8 text-center text-xs text-slate-400">
                    هنوز سفارشی ثبت نشده است
                  </td>
                </tr>
              )}
              {stats.recentOrders.map((o) => (
                <tr key={o.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3 font-num text-xs text-slate-500" dir="ltr">
                    {o.code}
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-700">
                    {o.fullName}
                  </td>
                  <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
                    {faDateTime(o.createdAt)}
                  </td>
                  <td className="px-3 py-3 text-xs font-bold text-slate-700 font-num">
                    {formatPrice(o.totalPrice)}
                  </td>
                  <td className="px-5 py-3 text-left">
                    <StatusBadge status={o.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="space-y-5">
          {/* هشدار موجودی */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="mb-3 text-sm font-bold text-slate-700">
              ⚠️ موجودی رو به اتمام
            </h2>
            {stats.lowStock.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-400">
                همه‌ی محصولات موجودی کافی دارند 👌
              </p>
            ) : (
              <ul className="space-y-2.5">
                {stats.lowStock.map((p) => (
                  <li key={p.id} className="flex items-center gap-2 text-xs">
                    <Link
                      href={`/admin/products/${p.id}`}
                      className="flex-1 truncate text-slate-600 hover:text-brand-700"
                    >
                      {p.title}
                    </Link>
                    <span
                      className={`rounded-md px-2 py-0.5 font-bold font-num ${
                        p.stock === 0
                          ? "bg-red-50 text-red-500"
                          : "bg-amber-50 text-amber-600"
                      }`}
                    >
                      {faNum(p.stock)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* پرفروش‌ترین‌ها */}
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="mb-3 text-sm font-bold text-slate-700">
              🏆 پرفروش‌ترین محصولات
            </h2>
            {stats.topProducts.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-400">
                هنوز فروشی ثبت نشده است
              </p>
            ) : (
              <ul className="space-y-2.5">
                {stats.topProducts.map((p, i) => (
                  <li key={p.product_id} className="flex items-center gap-2 text-xs">
                    <span className="grid h-5 w-5 shrink-0 place-items-center rounded-md bg-brand-50 font-bold text-brand-700 font-num">
                      {faNum(i + 1)}
                    </span>
                    <span className="flex-1 truncate text-slate-600">
                      {p.title}
                    </span>
                    <span className="text-slate-400 font-num">
                      {faNum(p.qty)} عدد
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
