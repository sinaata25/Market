"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { faNum, faDateTime, Pager, EmptyRow } from "@/components/admin/ui";

type ModerationStatus = "pending" | "approved" | "rejected";

type ProductComment = {
  id: number;
  content: string;
  type: "comment" | "question";
  status: ModerationStatus;
  parentId: number | null;
  createdAt: string;
  updatedAt: string;
  author: string;
  productId: number;
  productTitle: string;
  isAdminResponse: boolean;
  isVerifiedPurchase: boolean;
};

const statusLabel: Record<ModerationStatus, string> = {
  pending: "در انتظار تایید",
  approved: "تایید شده",
  rejected: "رد شده",
};

export default function AdminComments() {
  const [comments, setComments] = useState<ProductComment[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<ModerationStatus | "">("pending");
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [respondingTo, setRespondingTo] = useState<number | null>(null);
  const [responseText, setResponseText] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    const statusQuery = status ? `&status=${status}` : "";
    api
      .get<{ comments: ProductComment[]; pages: number; total: number }>(
        `/api/admin/comments?page=${page}${statusQuery}`
      )
      .then((result) => {
        if (result.ok && result.data) {
          setComments(result.data.comments);
          setPages(result.data.pages);
          setTotal(result.data.total);
        } else {
          setError(result.error ?? "خطا در دریافت پیام‌ها");
        }
        setLoading(false);
      });
  }, [page, status]);

  useEffect(() => {
    load();
  }, [load]);

  async function moderate(comment: ProductComment, next: ModerationStatus) {
    setUpdatingId(comment.id);
    setError("");
    const result = await api.patch(`/api/admin/comments/${comment.id}`, {
      status: next,
    });
    setUpdatingId(null);
    if (result.ok) load();
    else setError(result.error ?? "به‌روزرسانی وضعیت ناموفق بود");
  }

  async function remove(comment: ProductComment) {
    if (!confirm("این پیام و پاسخ‌های زیرمجموعه آن حذف شوند؟")) return;
    const result = await api.delete(`/api/admin/comments/${comment.id}`);
    if (result.ok) load();
    else setError(result.error ?? "حذف پیام ناموفق بود");
  }

  async function submitResponse(comment: ProductComment) {
    setUpdatingId(comment.id);
    setError("");
    const result = await api.post(
      `/api/admin/comments/${comment.id}/responses`,
      { content: responseText }
    );
    setUpdatingId(null);
    if (!result.ok) {
      setError(result.error ?? "ثبت پاسخ مدیر ناموفق بود");
      return;
    }
    setRespondingTo(null);
    setResponseText("");
    load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          دیدگاه‌ها و پرسش‌ها{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(total)})
          </span>
        </h1>
        <select
          value={status}
          onChange={(event) => {
            setLoading(true);
            setStatus(event.target.value as ModerationStatus | "");
            setPage(1);
          }}
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600"
        >
          <option value="pending">در انتظار تایید</option>
          <option value="approved">تاییدشده</option>
          <option value="rejected">ردشده</option>
          <option value="">همه پیام‌ها</option>
        </select>
      </div>

      {error && (
        <p className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-600">
          {error}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[900px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">پیام</th>
              <th className="px-3 py-3 font-medium">محصول</th>
              <th className="px-3 py-3 font-medium">نویسنده</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-3 py-3 font-medium">تاریخ</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={6} text="در حال بارگذاری..." />
            ) : comments.length === 0 ? (
              <EmptyRow colSpan={6} text="پیامی با این وضعیت وجود ندارد" />
            ) : (
              comments.map((comment) => (
                <tr key={comment.id} className="align-top hover:bg-slate-50/60">
                  <td className="max-w-[320px] px-5 py-3">
                    <div className="mb-1 flex flex-wrap gap-1">
                      {comment.type === "question" && (
                        <span className="rounded bg-sky-50 px-1.5 py-0.5 text-[9px] font-bold text-sky-700">
                          پرسش
                        </span>
                      )}
                      {comment.isAdminResponse && (
                        <span className="rounded bg-brand-50 px-1.5 py-0.5 text-[9px] font-bold text-brand-700">
                          پاسخ رسمی مدیر
                        </span>
                      )}
                      {comment.isVerifiedPurchase && !comment.isAdminResponse && (
                        <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700">
                          خریدار تاییدشده
                        </span>
                      )}
                      {comment.parentId && (
                        <span className="text-[9px] text-slate-400 font-num">
                          پاسخ به #{faNum(comment.parentId)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs leading-6 text-slate-600">
                      {comment.content}
                    </p>
                    {respondingTo === comment.id && (
                      <div className="mt-3 space-y-2">
                        <textarea
                          value={responseText}
                          onChange={(event) => setResponseText(event.target.value)}
                          maxLength={2000}
                          placeholder="پاسخ رسمی فروشگاه"
                          className="min-h-20 w-full rounded-lg border border-slate-200 p-2 text-xs outline-none focus:border-brand-400"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => submitResponse(comment)}
                            disabled={
                              updatingId === comment.id ||
                              responseText.trim().length < 2
                            }
                            className="rounded-md bg-brand-600 px-2 py-1 text-[10px] font-bold text-white disabled:opacity-50"
                          >
                            ثبت پاسخ
                          </button>
                          <button
                            onClick={() => {
                              setRespondingTo(null);
                              setResponseText("");
                            }}
                            className="text-[10px] text-slate-400"
                          >
                            انصراف
                          </button>
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-3">
                    <Link
                      href={`/product/${comment.productId}`}
                      className="block max-w-[160px] truncate text-xs text-brand-600 hover:underline"
                    >
                      {comment.productTitle}
                    </Link>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500">
                    {comment.author}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`rounded-md px-2 py-1 text-[10px] font-bold ${
                        comment.status === "approved"
                          ? "bg-emerald-50 text-emerald-600"
                          : comment.status === "rejected"
                            ? "bg-red-50 text-red-600"
                            : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {statusLabel[comment.status]}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
                    {faDateTime(comment.createdAt)}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex max-w-48 flex-wrap items-center gap-2">
                      {comment.status !== "approved" && (
                        <button
                          onClick={() => moderate(comment, "approved")}
                          disabled={updatingId === comment.id}
                          className="text-xs font-medium text-emerald-600 disabled:opacity-50"
                        >
                          تایید
                        </button>
                      )}
                      {comment.status !== "rejected" && !comment.isAdminResponse && (
                        <button
                          onClick={() => moderate(comment, "rejected")}
                          disabled={updatingId === comment.id}
                          className="text-xs font-medium text-amber-600 disabled:opacity-50"
                        >
                          رد / لغو انتشار
                        </button>
                      )}
                      {comment.status === "approved" && (
                        <button
                          onClick={() => {
                            setRespondingTo(comment.id);
                            setResponseText("");
                          }}
                          className="text-xs font-medium text-brand-600"
                        >
                          پاسخ رسمی
                        </button>
                      )}
                      <button
                        onClick={() => remove(comment)}
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
