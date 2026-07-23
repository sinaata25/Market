"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { formatPrice } from "@/lib/products";
import { STATUS_FA, StatusBadge, faNum, faDateTime } from "@/components/admin/ui";

type Order = {
  id: number;
  code: string;
  status: string;
  createdAt: string;
  city: string;
  province: string;
  totalPrice: number;
  discount: number;
  items: { id: number; title: string; qty: number; price: number }[];
};

const TABS = [
  { key: "", label: "همه" },
  { key: "PENDING", label: "در انتظار پرداخت" },
  { key: "PAID", label: "پرداخت شده" },
  { key: "SHIPPED", label: "ارسال شده" },
  { key: "DELIVERED", label: "تحویل شده" },
  { key: "CANCELED", label: "لغو شده" },
];

export default function MyOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [tab, setTab] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ orders: Order[] }>("/api/orders").then((res) => {
      if (res.ok && res.data) setOrders(res.data.orders);
      setLoading(false);
    });
  }, []);

  const visible = tab ? orders.filter((o) => o.status === tab) : orders;

  if (loading) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">
        سفارش‌های من{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({faNum(orders.length)})
        </span>
      </h1>

      {/* تب‌ها */}
      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => {
          const count = t.key
            ? orders.filter((o) => o.status === t.key).length
            : orders.length;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`rounded-lg px-3.5 py-1.5 text-xs transition ${
                tab === t.key
                  ? "bg-slate-800 font-medium text-white"
                  : "bg-white text-slate-500 ring-1 ring-slate-200 hover:text-slate-800"
              }`}
            >
              {t.label}
              {count > 0 && (
                <span className="mr-1 font-num opacity-70">
                  ({faNum(count)})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {visible.length === 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-5xl">📦</span>
          <p className="mb-6 text-sm text-slate-500">
            {tab
              ? `سفارشی با وضعیت «${STATUS_FA[tab]?.label}» ندارید`
              : "هنوز سفارشی ثبت نکرده‌اید"}
          </p>
          <Link
            href="/"
            className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            شروع خرید
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map((o) => (
            <Link
              key={o.id}
              href={`/profile/orders/${o.id}`}
              className="block rounded-2xl border border-slate-100 bg-white p-5 transition hover:border-brand-200 hover:shadow-sm"
            >
              <div className="mb-3 flex flex-wrap items-center gap-3 border-b border-slate-50 pb-3 text-xs">
                <code dir="ltr" className="font-num text-slate-500">
                  {o.code}
                </code>
                <span className="text-slate-300">|</span>
                <span className="text-slate-400 font-num">
                  {faDateTime(o.createdAt)}
                </span>
                <span className="text-slate-300">|</span>
                <span className="text-slate-400">
                  {o.province}، {o.city}
                </span>
                <span className="mr-auto">
                  <StatusBadge status={o.status} />
                </span>
              </div>

              <ul className="mb-3 space-y-1.5">
                {o.items.slice(0, 3).map((it) => (
                  <li
                    key={it.id}
                    className="flex justify-between gap-3 text-xs text-slate-600"
                  >
                    <span className="truncate">
                      {it.title}{" "}
                      <span className="text-slate-400 font-num">
                        ×{faNum(it.qty)}
                      </span>
                    </span>
                    <span className="shrink-0 font-num text-slate-500">
                      {formatPrice(it.price * it.qty)}
                    </span>
                  </li>
                ))}
                {o.items.length > 3 && (
                  <li className="text-[11px] text-slate-400 font-num">
                    و {faNum(o.items.length - 3)} کالای دیگر...
                  </li>
                )}
              </ul>

              <div className="flex items-center justify-between border-t border-slate-50 pt-3">
                <span className="text-xs text-brand-600">مشاهده جزئیات ←</span>
                <span className="text-sm font-bold text-slate-800 font-num">
                  {formatPrice(o.totalPrice)}
                  <span className="mr-1 text-[11px] font-normal text-slate-400">
                    تومان
                  </span>
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
