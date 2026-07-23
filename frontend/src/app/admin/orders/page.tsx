"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { formatPrice } from "@/lib/products";
import {
  STATUS_FA,
  faNum,
  faDateTime,
  Pager,
  EmptyRow,
} from "@/components/admin/ui";

type Order = {
  id: number;
  code: string;
  status: string;
  createdAt: string;
  fullName: string;
  phone: string;
  province: string;
  city: string;
  address: string;
  postalCode: string;
  discount: number;
  shippingPrice: number;
  totalPrice: number;
  items: { id: number; title: string; price: number; qty: number }[];
};

const TABS = [
  { key: "", label: "همه" },
  ...Object.entries(STATUS_FA).map(([key, s]) => ({ key, label: s.label })),
];

export default function AdminOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    if (search.trim()) qs.set("search", search.trim());
    qs.set("page", String(page));
    api
      .get<{ orders: Order[]; pages: number; total: number }>(
        `/api/admin/orders?${qs}`
      )
      .then((res) => {
        if (res.ok && res.data) {
          setOrders(res.data.orders);
          setPages(res.data.pages);
          setTotal(res.data.total);
        }
        setLoading(false);
      });
  }, [status, search, page]);

  useEffect(() => {
    load();
  }, [load]);

  async function changeStatus(order: Order, newStatus: string) {
    const res = await api.patch<{ order: Order }>(
      `/api/admin/orders/${order.id}`,
      { status: newStatus }
    );
    if (res.ok && res.data) {
      setOrders((prev) =>
        prev.map((o) => (o.id === order.id ? res.data!.order : o))
      );
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          سفارش‌ها{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(total)})
          </span>
        </h1>
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="جستجو: کد، نام، شماره..."
          className="w-56 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400"
        />
      </div>

      {/* تب‌های وضعیت */}
      <div className="flex flex-wrap gap-1.5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => {
              setStatus(t.key);
              setPage(1);
            }}
            className={`rounded-lg px-3.5 py-1.5 text-xs transition ${
              status === t.key
                ? "bg-slate-800 font-medium text-white"
                : "bg-white text-slate-500 ring-1 ring-slate-200 hover:text-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* جدول */}
      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">کد</th>
              <th className="px-3 py-3 font-medium">مشتری</th>
              <th className="px-3 py-3 font-medium">تاریخ</th>
              <th className="px-3 py-3 font-medium">مبلغ</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-5 py-3 font-medium">جزئیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={6} text="در حال بارگذاری..." />
            ) : orders.length === 0 ? (
              <EmptyRow colSpan={6} text="سفارشی یافت نشد" />
            ) : (
              orders.map((o) => (
                <OrderRow
                  key={o.id}
                  order={o}
                  expanded={expanded === o.id}
                  onToggle={() =>
                    setExpanded(expanded === o.id ? null : o.id)
                  }
                  onStatus={(s) => changeStatus(o, s)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pager page={page} pages={pages} onPage={setPage} />
    </div>
  );
}

function OrderRow({
  order: o,
  expanded,
  onToggle,
  onStatus,
}: {
  order: Order;
  expanded: boolean;
  onToggle: () => void;
  onStatus: (s: string) => void;
}) {
  return (
    <>
      <tr className="hover:bg-slate-50/60">
        <td className="px-5 py-3 text-xs font-num text-slate-500" dir="ltr">
          {o.code}
        </td>
        <td className="px-3 py-3">
          <p className="text-xs text-slate-700">{o.fullName}</p>
          <p className="text-[11px] text-slate-400 font-num" dir="ltr">
            {o.phone}
          </p>
        </td>
        <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
          {faDateTime(o.createdAt)}
        </td>
        <td className="px-3 py-3 text-xs font-bold text-slate-700 font-num">
          {formatPrice(o.totalPrice)}
        </td>
        <td className="px-3 py-3">
          <select
            value={o.status}
            onChange={(e) => onStatus(e.target.value)}
            className={`rounded-lg border-0 px-2 py-1.5 text-[11px] font-medium outline-none ring-1 ring-inset ring-slate-200 ${
              STATUS_FA[o.status]?.className ?? ""
            }`}
          >
            {Object.entries(STATUS_FA).map(([key, s]) => (
              <option key={key} value={key}>
                {s.label}
              </option>
            ))}
          </select>
        </td>
        <td className="px-5 py-3">
          <button
            onClick={onToggle}
            className="text-xs text-brand-600 hover:underline"
          >
            {expanded ? "بستن ▴" : "نمایش ▾"}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-slate-50/60">
          <td colSpan={6} className="px-5 py-4">
            <div className="grid gap-4 text-xs sm:grid-cols-2">
              <div>
                <p className="mb-2 font-bold text-slate-600">اقلام سفارش</p>
                <ul className="space-y-1.5">
                  {o.items.map((it) => (
                    <li key={it.id} className="flex justify-between gap-3">
                      <span className="text-slate-600">
                        {it.title}{" "}
                        <span className="text-slate-400 font-num">
                          ×{faNum(it.qty)}
                        </span>
                      </span>
                      <span className="shrink-0 text-slate-500 font-num">
                        {formatPrice(it.price * it.qty)}
                      </span>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 space-y-1 border-t border-slate-200 pt-2 text-[11px] text-slate-500">
                  {o.discount > 0 && (
                    <p className="flex justify-between">
                      <span>تخفیف</span>
                      <span className="font-num text-red-500">
                        {formatPrice(o.discount)}
                      </span>
                    </p>
                  )}
                  <p className="flex justify-between">
                    <span>هزینه ارسال</span>
                    <span className="font-num">
                      {o.shippingPrice === 0
                        ? "رایگان"
                        : formatPrice(o.shippingPrice)}
                    </span>
                  </p>
                </div>
              </div>
              <div>
                <p className="mb-2 font-bold text-slate-600">آدرس تحویل</p>
                <p className="leading-6 text-slate-500">
                  {o.province}، {o.city} — {o.address}
                  {o.postalCode && (
                    <>
                      <br />
                      کد پستی: <span className="font-num">{o.postalCode}</span>
                    </>
                  )}
                </p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
