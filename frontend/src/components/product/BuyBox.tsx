"use client";

import { useState } from "react";
import { formatPrice, type Product } from "@/lib/products";
import { api } from "@/lib/client-api";

export default function BuyBox({ product }: { product: Product }) {
  const [qty, setQty] = useState(1);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{
    type: "ok" | "error";
    text: string;
  } | null>(null);

  const discount = product.oldPrice
    ? Math.round((1 - product.price / product.oldPrice) * 100)
    : 0;

  const outOfStock = (product.stock ?? 0) < 1;

  async function addToCart() {
    setLoading(true);
    setMessage(null);
    const res = await api.post("/api/cart/items", {
      productId: product.id,
      qty,
    });
    setLoading(false);
    if (!res.ok) {
      setMessage({ type: "error", text: res.error ?? "خطا در افزودن به سبد" });
      return;
    }
    setMessage({ type: "ok", text: "به سبد خرید اضافه شد ✅" });
    // به بج سبد خرید در هدر خبر بده
    window.dispatchEvent(new CustomEvent("cart:updated"));
  }

  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-4 lg:sticky lg:top-28">
      {/* تضمین‌ها */}
      <ul className="mb-4 space-y-2.5 text-xs text-slate-600">
        <li className="flex items-center gap-2">
          <span className="text-brand-600">✅</span> {product.warranty}
        </li>
        <li className="flex items-center gap-2">
          <span className="text-brand-600">🚚</span> ارسال به سراسر کشور
        </li>
        <li className="flex items-center gap-2">
          <span className="text-brand-600">↩️</span> ۷ روز ضمانت بازگشت کالا
        </li>
      </ul>

      {/* موجودی */}
      {typeof product.stock === "number" &&
        product.stock > 0 &&
        product.stock <= 5 && (
          <p className="mb-3 text-xs font-medium text-red-500 font-num">
            تنها {product.stock.toLocaleString("fa-IR")} عدد در انبار باقی مانده
          </p>
        )}

      {/* قیمت */}
      <div className="mb-4">
        {product.oldPrice && (
          <div className="mb-1 flex items-center gap-2">
            <span className="rounded-md bg-accent-500 px-1.5 py-0.5 text-[11px] font-bold text-secondary-900 font-num">
              ٪{discount.toLocaleString("fa-IR")}
            </span>
            <span className="text-sm text-slate-300 line-through font-num">
              {formatPrice(product.oldPrice)}
            </span>
          </div>
        )}
        <div className="flex items-baseline justify-end gap-1">
          <span className="text-xl font-bold text-slate-800 font-num">
            {formatPrice(product.price)}
          </span>
          <span className="text-sm text-slate-400">تومان</span>
        </div>
      </div>

      {/* تعداد */}
      <div className="mb-4 flex items-center justify-between rounded-xl border border-slate-200 px-2 py-1.5">
        <span className="text-xs text-slate-500">تعداد</span>
        <div className="flex items-center gap-3">
          <button
            onClick={() =>
              setQty((q) => Math.min(product.stock ?? 99, q + 1))
            }
            disabled={qty >= (product.stock ?? 99)}
            aria-label="افزایش تعداد"
            className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-brand-600 hover:bg-slate-200 disabled:opacity-40"
          >
            +
          </button>
          <span className="w-6 text-center font-num text-sm">
            {qty.toLocaleString("fa-IR")}
          </span>
          <button
            onClick={() => setQty((q) => Math.max(1, q - 1))}
            disabled={qty <= 1}
            aria-label="کاهش تعداد"
            className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-slate-500 hover:bg-slate-200 disabled:opacity-40"
          >
            −
          </button>
        </div>
      </div>

      {/* افزودن به سبد */}
      <button
        onClick={addToCart}
        disabled={loading || outOfStock}
        className="w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {outOfStock
          ? "ناموجود"
          : loading
            ? "در حال افزودن..."
            : "افزودن به سبد خرید"}
      </button>

      {message && (
        <p
          className={`mt-3 text-center text-xs ${
            message.type === "ok" ? "text-brand-700" : "text-red-500"
          }`}
        >
          {message.text}
        </p>
      )}
    </div>
  );
}
