"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { faNum, faDateTime, Pager, EmptyRow } from "@/components/admin/ui";

type Review = {
  id: number;
  rating: number;
  text: string;
  createdAt: string;
  author: string;
  productId: number;
  productTitle: string;
  isPublished: boolean;
};

export default function AdminReviews() {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api
      .get<{ reviews: Review[]; pages: number; total: number }>(
        `/api/admin/reviews?page=${page}`
      )
      .then((res) => {
        if (res.ok && res.data) {
          setReviews(res.data.reviews);
          setPages(res.data.pages);
          setTotal(res.data.total);
        }
        setLoading(false);
      });
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(r: Review) {
    if (!confirm("این دیدگاه حذف شود؟ میانگین امتیاز محصول به‌روز می‌شود.")) {
      return;
    }
    const res = await api.delete(`/api/admin/reviews/${r.id}`);
    if (res.ok) load();
    else setError(res.error ?? "حذف دیدگاه ناموفق بود");
  }

  async function setPublished(r: Review, isPublished: boolean) {
    setUpdatingId(r.id);
    setError("");
    const res = await api.patch(`/api/admin/reviews/${r.id}`, {
      isPublished,
    });
    setUpdatingId(null);
    if (res.ok) load();
    else setError(res.error ?? "به‌روزرسانی وضعیت دیدگاه ناموفق بود");
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">
        دیدگاه‌ها{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({faNum(total)})
        </span>
      </h1>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-600">
          {error}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">دیدگاه</th>
              <th className="px-3 py-3 font-medium">محصول</th>
              <th className="px-3 py-3 font-medium">نویسنده</th>
              <th className="px-3 py-3 font-medium">امتیاز</th>
              <th className="px-3 py-3 font-medium">تاریخ</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={7} text="در حال بارگذاری..." />
            ) : reviews.length === 0 ? (
              <EmptyRow colSpan={7} text="دیدگاهی ثبت نشده است" />
            ) : (
              reviews.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/60">
                  <td className="max-w-[260px] px-5 py-3">
                    <p className="truncate text-xs leading-6 text-slate-600">
                      {r.text}
                    </p>
                  </td>
                  <td className="px-3 py-3">
                    <Link
                      href={`/product/${r.productId}`}
                      className="block max-w-[160px] truncate text-xs text-brand-600 hover:underline"
                    >
                      {r.productTitle}
                    </Link>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500">
                    {r.author}
                  </td>
                  <td className="px-3 py-3">
                    <span className="rounded-md bg-amber-50 px-2 py-1 text-[11px] font-bold text-amber-600 font-num">
                      ★ {faNum(r.rating)}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
                    {faDateTime(r.createdAt)}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`rounded-md px-2 py-1 text-[11px] font-bold ${
                        r.isPublished
                          ? "bg-emerald-50 text-emerald-600"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {r.isPublished ? "منتشر شده" : "در انتظار تایید"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setPublished(r, !r.isPublished)}
                        disabled={updatingId === r.id}
                        className="text-xs font-medium text-brand-600 hover:text-brand-700 disabled:opacity-50"
                      >
                        {updatingId === r.id
                          ? "در حال ثبت..."
                          : r.isPublished
                            ? "لغو انتشار"
                            : "تایید و انتشار"}
                      </button>
                      <button
                        onClick={() => remove(r)}
                        className="text-xs text-red-400 hover:text-red-600"
                      >
                        حذف
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pager page={page} pages={pages} onPage={setPage} />
    </div>
  );
}
