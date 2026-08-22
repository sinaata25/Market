"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { formatPrice } from "@/lib/products";
import { StatusBadge, faNum, faDateTime } from "@/components/admin/ui";

type Order = {
  id: number;
  code: string;
  status: string;
  statusLabel: string;
  createdAt: string;
  fullName: string;
  phone: string;
  province: string;
  city: string;
  address: string;
  postalCode: string;
  itemsPrice: number;
  discount: number;
  shippingPrice: number;
  totalPrice: number;
  canCancel: boolean;
  items: {
    id: number;
    title: string;
    price: number;
    oldPrice: number | null;
    qty: number;
    productId: number;
  }[];
};

// مراحل پیشرفت سفارش
const STEPS = [
  { key: "PENDING", label: "ثبت سفارش", icon: "📝" },
  { key: "PAID", label: "پرداخت", icon: "💳" },
  { key: "SHIPPED", label: "ارسال", icon: "🚚" },
  { key: "DELIVERED", label: "تحویل", icon: "✅" },
];

export default function OrderDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [order, setOrder] = useState<Order | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [canceling, setCanceling] = useState(false);
  const [downloadingInvoice, setDownloadingInvoice] = useState(false);
  const [invoiceError, setInvoiceError] = useState("");

  const load = useCallback(() => {
    api.get<{ order: Order }>(`/api/orders/${id}`).then((res) => {
      if (res.ok && res.data) setOrder(res.data.order);
      else setNotFound(true);
    });
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function cancel() {
    if (!confirm("این سفارش لغو شود؟ موجودی کالاها به انبار بازمی‌گردد.")) {
      return;
    }
    setCanceling(true);
    const res = await api.post<{ order: Order }>(`/api/orders/${id}`);
    setCanceling(false);
    if (res.ok && res.data) setOrder(res.data.order);
  }

  if (notFound) {
    return (
      <div className="rounded-2xl border border-slate-100 bg-white px-6 py-16 text-center">
        <span className="mb-4 block text-5xl">🔍</span>
        <p className="mb-6 text-sm text-slate-500">سفارش یافت نشد</p>
        <Link
          href="/profile/orders"
          className="text-sm text-brand-600 hover:underline"
        >
          → بازگشت به سفارش‌ها
        </Link>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  const isCanceled = order.status === "CANCELED";
  const currentStep = STEPS.findIndex((s) => s.key === order.status);
  const invoiceFallbackFilename = `invoice-${order.code}.pdf`;

  async function downloadInvoice() {
    setDownloadingInvoice(true);
    setInvoiceError("");

    try {
      const result = await api.downloadPdf(
        `/api/orders/${id}/invoice`,
        invoiceFallbackFilename
      );
      if (!result.ok || !result.data) {
        setInvoiceError(result.error ?? "دریافت فاکتور با خطا روبه‌رو شد");
        return;
      }

      const objectUrl = window.URL.createObjectURL(result.data.blob);
      const link = document.createElement("a");
      try {
        link.href = objectUrl;
        link.download = result.data.filename;
        link.hidden = true;
        document.body.appendChild(link);
        link.click();
      } finally {
        link.remove();
        window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1_000);
      }
    } catch {
      setInvoiceError("ذخیره فاکتور در مرورگر با خطا روبه‌رو شد");
    } finally {
      setDownloadingInvoice(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <Link
          href="/profile/orders"
          className="text-xs text-slate-400 hover:text-brand-600"
        >
          → سفارش‌های من
        </Link>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-bold text-slate-800">
            سفارش{" "}
            <code dir="ltr" className="font-num text-brand-600">
              {order.code}
            </code>
          </h1>
          <StatusBadge status={order.status} />
        </div>
        <p className="mt-1 text-xs text-slate-400 font-num">
          ثبت شده در {faDateTime(order.createdAt)}
        </p>
      </div>

      {/* نوار پیشرفت */}
      {!isCanceled ? (
        <div className="rounded-2xl border border-slate-100 bg-white p-6">
          <div className="flex items-center">
            {STEPS.map((step, i) => {
              const done = i <= currentStep;
              return (
                <div key={step.key} className="flex flex-1 items-center">
                  <div className="flex flex-col items-center gap-2">
                    <span
                      className={`grid h-10 w-10 place-items-center rounded-full text-lg transition ${
                        done
                          ? "bg-brand-600 text-white"
                          : "bg-slate-100 text-slate-300"
                      }`}
                    >
                      {step.icon}
                    </span>
                    <span
                      className={`whitespace-nowrap text-[11px] ${
                        done ? "font-medium text-brand-700" : "text-slate-400"
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div
                      className={`mx-2 h-0.5 flex-1 rounded-full ${
                        i < currentStep ? "bg-brand-600" : "bg-slate-100"
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-5 text-center text-sm text-red-500">
          این سفارش لغو شده است و موجودی کالاها به انبار بازگشته.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {/* اقلام */}
        <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white lg:col-span-2">
          <h2 className="border-b border-slate-100 px-5 py-4 text-sm font-bold text-slate-700">
            کالاهای سفارش
          </h2>
          <ul className="divide-y divide-slate-50">
            {order.items.map((it) => (
              <li key={it.id} className="flex items-center gap-3 px-5 py-4">
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/product/${it.productId}`}
                    className="block truncate text-xs text-slate-700 hover:text-brand-700"
                  >
                    {it.title}
                  </Link>
                  <p className="mt-1 text-[11px] text-slate-400 font-num">
                    {faNum(it.qty)} عدد × {formatPrice(it.price)} تومان
                  </p>
                </div>
                <span className="shrink-0 text-sm font-bold text-slate-700 font-num">
                  {formatPrice(it.price * it.qty)}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* خلاصه پرداخت و آدرس */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="mb-3 text-sm font-bold text-slate-700">
              خلاصه پرداخت
            </h2>
            <ul className="space-y-2 text-xs">
              <li className="flex justify-between text-slate-500">
                <span>قیمت کالاها</span>
                <span className="font-num">
                  {formatPrice(order.itemsPrice)}
                </span>
              </li>
              {order.discount > 0 && (
                <li className="flex justify-between text-accent-700">
                  <span>سود شما از خرید</span>
                  <span className="font-num">
                    {formatPrice(order.discount)}
                  </span>
                </li>
              )}
              <li className="flex justify-between text-slate-500">
                <span>هزینه ارسال</span>
                <span className="font-num">
                  {order.shippingPrice === 0
                    ? "رایگان"
                    : formatPrice(order.shippingPrice)}
                </span>
              </li>
              <li className="flex justify-between border-t border-slate-100 pt-2 text-sm font-bold text-slate-800">
                <span>مبلغ کل</span>
                <span className="font-num">
                  {formatPrice(order.totalPrice)}
                </span>
              </li>
            </ul>
            <div className="mt-4 border-t border-slate-100 pt-4">
              <button
                type="button"
                onClick={downloadInvoice}
                disabled={downloadingInvoice}
                aria-busy={downloadingInvoice}
                aria-describedby={
                  invoiceError ? "invoice-download-error" : undefined
                }
                className="w-full rounded-xl bg-brand-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-wait disabled:opacity-60"
              >
                {downloadingInvoice
                  ? "در حال آماده‌سازی فاکتور..."
                  : "دانلود فاکتور"}
              </button>
              {invoiceError && (
                <p
                  id="invoice-download-error"
                  role="alert"
                  className="mt-2 text-xs leading-5 text-red-500"
                >
                  {invoiceError}
                </p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="mb-3 text-sm font-bold text-slate-700">
              اطلاعات تحویل
            </h2>
            <div className="space-y-1.5 text-xs leading-6 text-slate-500">
              <p className="text-slate-700">{order.fullName}</p>
              <p className="font-num" dir="ltr">
                {order.phone}
              </p>
              <p>
                {order.province}، {order.city}
              </p>
              <p>{order.address}</p>
              {order.postalCode && (
                <p className="font-num">کد پستی: {order.postalCode}</p>
              )}
            </div>
          </div>

          {order.canCancel && (
            <button
              onClick={cancel}
              disabled={canceling}
              className="w-full rounded-xl border border-red-200 bg-red-50 py-3 text-sm font-medium text-red-500 transition hover:bg-red-100 disabled:opacity-60"
            >
              {canceling ? "در حال لغو..." : "لغو سفارش"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
