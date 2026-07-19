"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatPrice } from "@/lib/products";

type Order = {
  id: number;
  code: string;
  status: string;
  createdAt: string;
  totalPrice: number;
  discount: number;
  fullName: string;
  city: string;
  province: string;
  items: { id: number; title: string; qty: number; price: number }[];
};

const STATUS_FA: Record<string, { label: string; className: string }> = {
  PENDING: { label: "در انتظار پرداخت", className: "bg-amber-50 text-amber-600" },
  PAID: { label: "پرداخت شده", className: "bg-blue-50 text-blue-600" },
  SHIPPED: { label: "ارسال شده", className: "bg-indigo-50 text-indigo-600" },
  DELIVERED: { label: "تحویل شده", className: "bg-brand-50 text-brand-700" },
  CANCELED: { label: "لغو شده", className: "bg-red-50 text-red-500" },
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [needLogin, setNeedLogin] = useState(false);

  useEffect(() => {
    fetch("/api/orders")
      .then((r) => {
        if (r.status === 401) {
          setNeedLogin(true);
          return null;
        }
        return r.json();
      })
      .then((json) => {
        if (json?.ok) setOrders(json.data.orders);
      })
      .catch(() => {});
  }, []);

  if (needLogin) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <span className="mb-4 block text-5xl">🔐</span>
        <p className="mb-6 text-sm text-slate-500">
          برای مشاهده سفارش‌ها ابتدا وارد حساب کاربری شوید.
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

  if (!orders) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 text-center text-sm text-slate-400">
        در حال بارگذاری سفارش‌ها...
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <span className="mb-4 block text-5xl">📦</span>
        <p className="mb-6 text-sm text-slate-500">
          هنوز سفارشی ثبت نکرده‌اید.
        </p>
        <Link
          href="/"
          className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          شروع خرید
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      <h1 className="mb-5 text-lg font-bold text-slate-800">سفارش‌های من</h1>
      <div className="space-y-4">
        {orders.map((o) => {
          const status = STATUS_FA[o.status] ?? STATUS_FA.PENDING;
          return (
            <div
              key={o.id}
              className="rounded-2xl border border-slate-100 bg-white p-5"
            >
              <div className="mb-4 flex flex-wrap items-center gap-3 border-b border-slate-100 pb-4 text-xs text-slate-500">
                <span className="font-num" dir="ltr">
                  {o.code}
                </span>
                <span className="text-slate-300">|</span>
                <span className="font-num">
                  {new Date(o.createdAt).toLocaleDateString("fa-IR")}
                </span>
                <span className="text-slate-300">|</span>
                <span>
                  {o.province}، {o.city} — {o.fullName}
                </span>
                <span
                  className={`mr-auto rounded-lg px-2.5 py-1 font-medium ${status.className}`}
                >
                  {status.label}
                </span>
              </div>

              <ul className="mb-4 space-y-2">
                {o.items.map((it) => (
                  <li
                    key={it.id}
                    className="flex justify-between gap-3 text-sm text-slate-600"
                  >
                    <span className="truncate">
                      {it.title}{" "}
                      <span className="text-xs text-slate-400 font-num">
                        ×{it.qty.toLocaleString("fa-IR")}
                      </span>
                    </span>
                    <span className="shrink-0 font-num">
                      {formatPrice(it.price * it.qty)} تومان
                    </span>
                  </li>
                ))}
              </ul>

              <div className="flex justify-between border-t border-slate-100 pt-3 text-sm font-bold text-slate-800">
                <span>مبلغ کل</span>
                <span className="font-num">
                  {formatPrice(o.totalPrice)} تومان
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
