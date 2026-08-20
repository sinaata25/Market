"use client";

import Link from "next/link";
import { formatPrice } from "@/lib/products";
import { MAX_COMPARE_ITEMS, useCompare } from "@/lib/compare";

// نوار شناور مقایسه — هنگام مرور فروشگاه، محصولات انتخاب‌شده را نشان می‌دهد
export default function CompareTray() {
  const { items, count, canCompare, remove, clear } = useCompare();

  if (count === 0) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 shadow-[0_-4px_16px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3">
        <div className="flex flex-1 items-center gap-2 overflow-x-auto">
          {items.map((item) => (
            <div
              key={item.id}
              className="flex shrink-0 items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 py-1 pr-1 pl-2.5"
            >
              <div className="grid h-9 w-9 place-items-center overflow-hidden rounded-lg bg-white">
                {item.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.image}
                    alt={item.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <span className="text-xs text-slate-300">—</span>
                )}
              </div>
              <div className="max-w-28 text-right">
                <p className="line-clamp-1 text-[11px] font-medium text-slate-700">
                  {item.title}
                </p>
                <p className="text-[11px] text-slate-400 font-num">
                  {formatPrice(item.price)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => remove(item.id)}
                aria-label={`حذف ${item.title} از مقایسه`}
                title="حذف از مقایسه"
                className="grid h-6 w-6 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-200 hover:text-slate-600"
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="whitespace-nowrap text-xs text-slate-400 font-num">
            {count.toLocaleString("fa-IR")} از {MAX_COMPARE_ITEMS.toLocaleString("fa-IR")}
          </span>
          <button
            type="button"
            onClick={clear}
            className="whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium text-slate-500 transition hover:bg-slate-100"
          >
            پاک کردن
          </button>
          <Link
            href="/compare"
            aria-disabled={!canCompare}
            className={`whitespace-nowrap rounded-xl px-4 py-2.5 text-xs font-bold text-white shadow-sm transition ${
              canCompare
                ? "bg-brand-600 hover:bg-brand-700"
                : "pointer-events-none bg-slate-300"
            }`}
          >
            مقایسه محصولات
          </Link>
        </div>
      </div>
    </div>
  );
}
