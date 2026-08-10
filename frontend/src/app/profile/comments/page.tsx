"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { faNum, faDateTime } from "@/components/admin/ui";

type ProductComment = {
  id: number;
  content: string;
  type: "comment" | "question";
  status: "pending" | "approved" | "rejected";
  parentId: number | null;
  createdAt: string;
  productId: number;
  productTitle: string;
  isVerifiedPurchase: boolean;
};

const statusLabels = {
  pending: "در انتظار تایید",
  approved: "منتشر شده",
  rejected: "رد شده",
} as const;

export default function MyComments() {
  const [comments, setComments] = useState<ProductComment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get<{ comments: ProductComment[] }>("/api/auth/my-comments").then((result) => {
      if (result.ok && result.data) setComments(result.data.comments);
      else setError(result.error ?? "خطا در دریافت دیدگاه‌ها");
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(comment: ProductComment) {
    if (!confirm("این پیام حذف شود؟")) return;
    const result = await api.delete("/api/auth/my-comments", {
      commentId: comment.id,
    });
    if (result.ok) load();
    else setError(result.error ?? "حذف پیام ناموفق بود");
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
        دیدگاه‌ها و پرسش‌های من{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({faNum(comments.length)})
        </span>
      </h1>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-600">
          {error}
        </p>
      )}

      {comments.length === 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-5xl">💬</span>
          <p className="mb-2 text-sm font-bold text-slate-700">
            هنوز پیامی ثبت نکرده‌اید
          </p>
          <p className="mb-6 text-xs text-slate-500">
            می‌توانید بدون نیاز به خرید، در صفحه هر محصول دیدگاه یا پرسش ثبت کنید.
          </p>
          <Link
            href="/"
            className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مشاهده محصولات
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {comments.map((comment) => (
            <div
              key={comment.id}
              className="rounded-2xl border border-slate-100 bg-white p-5"
            >
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/product/${comment.productId}`}
                    className="block truncate text-xs font-medium text-slate-700 hover:text-brand-700"
                  >
                    {comment.productTitle}
                  </Link>
                  <p className="mt-0.5 text-[11px] text-slate-400 font-num">
                    {faDateTime(comment.createdAt)}
                  </p>
                </div>
                {comment.type === "question" && (
                  <span className="rounded-lg bg-sky-50 px-2.5 py-1 text-[10px] font-bold text-sky-700">
                    پرسش
                  </span>
                )}
                {comment.isVerifiedPurchase && (
                  <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700">
                    خریدار تاییدشده
                  </span>
                )}
                <span
                  className={`rounded-lg px-2.5 py-1 text-[10px] font-bold ${
                    comment.status === "approved"
                      ? "bg-emerald-50 text-emerald-600"
                      : comment.status === "rejected"
                        ? "bg-red-50 text-red-600"
                        : "bg-amber-50 text-amber-700"
                  }`}
                >
                  {statusLabels[comment.status]}
                </span>
              </div>
              <p className="text-xs leading-6 text-slate-600">
                {comment.content}
              </p>
              <div className="mt-3 border-t border-slate-50 pt-3">
                <button
                  onClick={() => remove(comment)}
                  className="text-xs text-red-400 hover:text-red-600"
                >
                  حذف پیام
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
