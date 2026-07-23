"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { faNum, faDateTime } from "@/components/admin/ui";

type Review = {
  id: number;
  rating: number;
  text: string;
  createdAt: string;
  productId: number;
  productTitle: string;
  productEmoji: string;
};

export default function MyReviews() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.get<{ reviews: Review[] }>("/api/auth/my-reviews").then((res) => {
      if (res.ok && res.data) setReviews(res.data.reviews);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(r: Review) {
    if (!confirm("این دیدگاه حذف شود؟")) return;
    const res = await api.delete("/api/auth/my-reviews", { reviewId: r.id });
    if (res.ok) load();
  }

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
        دیدگاه‌های من{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({faNum(reviews.length)})
        </span>
      </h1>

      {reviews.length === 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-5xl">💬</span>
          <p className="mb-2 text-sm font-bold text-slate-700">
            هنوز دیدگاهی ثبت نکرده‌اید
          </p>
          <p className="mb-6 text-xs text-slate-500">
            نظر شما به سایر خریداران در انتخاب بهتر کمک می‌کند.
          </p>
          <Link
            href="/profile/orders"
            className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مشاهده خریدهای من
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {reviews.map((r) => (
            <div
              key={r.id}
              className="rounded-2xl border border-slate-100 bg-white p-5"
            >
              <div className="mb-3 flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-slate-50 text-xl">
                  {r.productEmoji}
                </span>
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/product/${r.productId}`}
                    className="block truncate text-xs font-medium text-slate-700 hover:text-brand-700"
                  >
                    {r.productTitle}
                  </Link>
                  <p className="mt-0.5 text-[11px] text-slate-400 font-num">
                    {faDateTime(r.createdAt)}
                  </p>
                </div>
                <span className="shrink-0 rounded-lg bg-amber-50 px-2.5 py-1 text-[11px] font-bold text-amber-600 font-num">
                  ★ {faNum(r.rating)}
                </span>
              </div>
              <p className="text-xs leading-6 text-slate-600">{r.text}</p>
              <div className="mt-3 border-t border-slate-50 pt-3">
                <button
                  onClick={() => remove(r)}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  حذف دیدگاه
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
