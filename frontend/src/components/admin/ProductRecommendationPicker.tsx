"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/client-api";
import { formatPrice, type Product } from "@/lib/products";

const MAX_RECOMMENDATIONS = 3;

export default function ProductRecommendationPicker({
  sourceProductId,
  selected,
  onChange,
  disabled = false,
}: {
  sourceProductId?: number;
  selected: Product[];
  onChange: (products: Product[]) => void;
  disabled?: boolean;
}) {
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);

  useEffect(() => {
    const currentRequest = ++requestId.current;
    const timer = window.setTimeout(() => {
      setLoading(true);
      const query = new URLSearchParams({ page: "1" });
      if (search.trim()) query.set("search", search.trim());
      api
        .get<{ products: Product[] }>(`/api/admin/products?${query}`)
        .then((result) => {
          if (requestId.current !== currentRequest) return;
          setResults(result.ok ? (result.data?.products ?? []) : []);
          setLoading(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      requestId.current += 1;
    };
  }, [search]);

  const selectedIds = new Set(selected.map((product) => product.id));
  const candidates = results.filter(
    (product) => product.id !== sourceProductId && !selectedIds.has(product.id)
  );

  function add(product: Product) {
    if (disabled || selected.length >= MAX_RECOMMENDATIONS) return;
    onChange([...selected, product]);
    setSearch("");
  }

  function remove(productId: number) {
    if (disabled) return;
    onChange(selected.filter((product) => product.id !== productId));
  }

  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-5">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-700">محصولات پیشنهادی</h2>
          <p className="mt-1 text-[11px] leading-5 text-slate-400">
            حداکثر ۳ محصول مکمل که پیش از ثبت سفارش به مشتری پیشنهاد می‌شوند.
          </p>
        </div>
        <span className="shrink-0 rounded-lg bg-slate-100 px-2 py-1 text-[11px] text-slate-500 font-num">
          {selected.length.toLocaleString("fa-IR")} / ۳
        </span>
      </div>

      {selected.length > 0 && (
        <div className="mb-4 space-y-2">
          {selected.map((product, index) => (
            <div
              key={product.id}
              className="flex items-center gap-3 rounded-xl border border-brand-100 bg-brand-50/40 p-2.5"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-[11px] text-brand-700 font-num">
                {(index + 1).toLocaleString("fa-IR")}
              </span>
              {product.image && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={product.image}
                  alt=""
                  className="h-10 w-10 shrink-0 rounded-lg object-cover"
                />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium text-slate-700">
                  {product.title}
                </p>
                <p className="mt-0.5 text-[10px] text-slate-400 font-num">
                  {formatPrice(product.price)} تومان
                </p>
              </div>
              <button
                type="button"
                disabled={disabled}
                onClick={() => remove(product.id)}
                className="shrink-0 rounded-lg px-2 py-1 text-[11px] text-red-500 transition hover:bg-red-50 disabled:opacity-50"
              >
                حذف
              </button>
            </div>
          ))}
        </div>
      )}

      <label>
        <span className="mb-1.5 block text-xs font-medium text-slate-600">
          جستجو و انتخاب محصول
        </span>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          disabled={disabled || selected.length >= MAX_RECOMMENDATIONS}
          placeholder={
            selected.length >= MAX_RECOMMENDATIONS
              ? "حداکثر ۳ محصول انتخاب شده است"
              : "نام محصول را جستجو کنید..."
          }
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white disabled:cursor-not-allowed disabled:opacity-60"
        />
      </label>

      {selected.length < MAX_RECOMMENDATIONS && (
        <div className="mt-2 max-h-52 overflow-y-auto rounded-xl border border-slate-100">
          {loading ? (
            <p className="p-4 text-center text-xs text-slate-400">در حال جستجو...</p>
          ) : candidates.length === 0 ? (
            <p className="p-4 text-center text-xs text-slate-400">
              محصول دیگری یافت نشد
            </p>
          ) : (
            candidates.map((product) => (
              <button
                key={product.id}
                type="button"
                disabled={disabled}
                onClick={() => add(product)}
                className="flex w-full items-center gap-3 border-b border-slate-50 px-3 py-2.5 text-right transition last:border-0 hover:bg-slate-50 disabled:opacity-50"
              >
                <span className="min-w-0 flex-1 truncate text-xs text-slate-700">
                  {product.title}
                </span>
                <span className="shrink-0 text-[10px] text-slate-400 font-num">
                  {formatPrice(product.price)} تومان
                </span>
                <span className="shrink-0 text-xs font-bold text-brand-600">+</span>
              </button>
            ))
          )}
        </div>
      )}
    </section>
  );
}
