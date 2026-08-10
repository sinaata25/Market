"use client";

import { useCallback, useState } from "react";
import type { Product } from "@/lib/products";
import { api } from "@/lib/client-api";

const tabs = [
  { key: "specs", label: "مشخصات" },
  { key: "intro", label: "معرفی" },
  { key: "ratings", label: "امتیازها" },
  { key: "comments", label: "دیدگاه‌ها و پرسش‌ها" },
] as const;

type TabKey = (typeof tabs)[number]["key"];

type RatingData = {
  average: number;
  count: number;
  myRating: number | null;
  canRate: boolean;
};

type CommentStatus = "pending" | "approved" | "rejected";

type ProductComment = {
  id: number;
  content: string;
  type: "comment" | "question";
  status: CommentStatus;
  parentId: number | null;
  createdAt: string;
  updatedAt: string;
  author: string;
  isAdminResponse: boolean;
  isVerifiedPurchase: boolean;
  replies: ProductComment[];
};

const statusLabels: Record<Exclude<CommentStatus, "approved">, string> = {
  pending: "در انتظار تایید",
  rejected: "رد شده",
};

function CommentCard({
  comment,
  depth = 0,
  replyingTo,
  replyText,
  submittingReply,
  onReply,
  onReplyText,
  onSubmitReply,
  onCancelReply,
}: {
  comment: ProductComment;
  depth?: number;
  replyingTo: number | null;
  replyText: string;
  submittingReply: boolean;
  onReply: (id: number) => void;
  onReplyText: (value: string) => void;
  onSubmitReply: (id: number) => void;
  onCancelReply: () => void;
}) {
  return (
    <div className={depth ? "mr-4 border-r-2 border-slate-100 pr-4" : ""}>
      <article
        className={`rounded-xl border p-4 ${
          comment.isAdminResponse
            ? "border-brand-100 bg-brand-50/50"
            : "border-slate-100 bg-white"
        }`}
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-sm font-bold text-slate-700">
            {comment.author}
          </span>
          {comment.isAdminResponse && (
            <span className="rounded-md bg-brand-600 px-2 py-0.5 text-[10px] font-bold text-white">
              مدیر فروشگاه
            </span>
          )}
          {!comment.isAdminResponse && comment.isVerifiedPurchase && (
            <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
              خریدار تاییدشده
            </span>
          )}
          {comment.type === "question" && (
            <span className="rounded-md bg-sky-50 px-2 py-0.5 text-[10px] font-bold text-sky-700">
              پرسش
            </span>
          )}
          {comment.status !== "approved" && (
            <span
              className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                comment.status === "pending"
                  ? "bg-amber-50 text-amber-700"
                  : "bg-red-50 text-red-600"
              }`}
            >
              {statusLabels[comment.status]}
            </span>
          )}
        </div>
        <p className="text-sm leading-7 text-slate-600">{comment.content}</p>
        {comment.status === "approved" && (
          <button
            type="button"
            onClick={() => onReply(comment.id)}
            className="mt-2 text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            پاسخ
          </button>
        )}

        {replyingTo === comment.id && (
          <div className="mt-3 space-y-2 rounded-lg bg-white p-3">
            <textarea
              value={replyText}
              onChange={(event) => onReplyText(event.target.value)}
              minLength={5}
              maxLength={2000}
              placeholder="پاسخ خود را بنویسید"
              className="min-h-20 w-full rounded-lg border border-slate-200 p-3 text-sm outline-none focus:border-brand-400"
            />
            <div className="flex gap-2">
              <button
                type="button"
                disabled={submittingReply || replyText.trim().length < 5}
                onClick={() => onSubmitReply(comment.id)}
                className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
              >
                {submittingReply ? "در حال ثبت..." : "ثبت پاسخ"}
              </button>
              <button
                type="button"
                onClick={onCancelReply}
                className="px-3 py-2 text-xs text-slate-500"
              >
                انصراف
              </button>
            </div>
          </div>
        )}
      </article>

      {comment.replies.length > 0 && (
        <div className="mt-3 space-y-3">
          {comment.replies.map((reply) => (
            <CommentCard
              key={reply.id}
              comment={reply}
              depth={depth + 1}
              replyingTo={replyingTo}
              replyText={replyText}
              submittingReply={submittingReply}
              onReply={onReply}
              onReplyText={onReplyText}
              onSubmitReply={onSubmitReply}
              onCancelReply={onCancelReply}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProductTabs({ product }: { product: Product }) {
  const [active, setActive] = useState<TabKey>("specs");
  const [ratingData, setRatingData] = useState<RatingData>({
    average: product.rating,
    count: product.ratingCount,
    myRating: null,
    canRate: false,
  });
  const [selectedRating, setSelectedRating] = useState(5);
  const [ratingLoading, setRatingLoading] = useState(false);
  const [ratingSubmitting, setRatingSubmitting] = useState(false);
  const [ratingMessage, setRatingMessage] = useState("");
  const [comments, setComments] = useState<ProductComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentType, setCommentType] = useState<"comment" | "question">(
    "comment"
  );
  const [commentText, setCommentText] = useState("");
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const [commentMessage, setCommentMessage] = useState("");
  const [replyingTo, setReplyingTo] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");
  const [submittingReply, setSubmittingReply] = useState(false);

  const loadRating = useCallback(async () => {
    const result = await api.get<{ rating: RatingData }>(
      `/api/products/${product.id}/rating`
    );
    if (result.ok && result.data) {
      setRatingData(result.data.rating);
      setSelectedRating(result.data.rating.myRating ?? 5);
    } else {
      setRatingMessage(result.error ?? "خطا در دریافت امتیازها");
    }
    setRatingLoading(false);
  }, [product.id]);

  const loadComments = useCallback(async () => {
    const result = await api.get<{ comments: ProductComment[] }>(
      `/api/products/${product.id}/comments`
    );
    if (result.ok && result.data) setComments(result.data.comments);
    else setCommentMessage(result.error ?? "خطا در دریافت دیدگاه‌ها");
    setCommentsLoading(false);
  }, [product.id]);

  async function submitRating() {
    setRatingSubmitting(true);
    setRatingMessage("");
    const result = await api.put<{
      rating: { value: number; average: number; count: number };
    }>(`/api/products/${product.id}/rating`, { rating: selectedRating });
    setRatingSubmitting(false);
    if (!result.ok || !result.data) {
      setRatingMessage(
        result.status === 401
          ? "برای امتیازدهی ابتدا وارد حساب شوید"
          : (result.error ?? "خطا در ثبت امتیاز")
      );
      return;
    }
    setRatingData((current) => ({
      ...current,
      average: result.data!.rating.average,
      count: result.data!.rating.count,
      myRating: result.data!.rating.value,
    }));
    setRatingMessage("امتیاز شما ثبت شد.");
  }

  async function submitComment(event: React.FormEvent) {
    event.preventDefault();
    setCommentSubmitting(true);
    setCommentMessage("");
    const result = await api.post(
      `/api/products/${product.id}/comments`,
      { content: commentText, type: commentType }
    );
    setCommentSubmitting(false);
    if (!result.ok) {
      setCommentMessage(
        result.status === 401
          ? "برای ثبت دیدگاه ابتدا وارد حساب شوید"
          : (result.error ?? "خطا در ثبت دیدگاه")
      );
      return;
    }
    setCommentText("");
    setCommentMessage("پیام شما ثبت شد و پس از تایید مدیر منتشر می‌شود.");
    await loadComments();
  }

  async function submitReply(parentId: number) {
    setSubmittingReply(true);
    setCommentMessage("");
    const result = await api.post(
      `/api/products/${product.id}/comments`,
      { content: replyText, parentId }
    );
    setSubmittingReply(false);
    if (!result.ok) {
      setCommentMessage(
        result.status === 401
          ? "برای ثبت پاسخ ابتدا وارد حساب شوید"
          : (result.error ?? "خطا در ثبت پاسخ")
      );
      return;
    }
    setReplyText("");
    setReplyingTo(null);
    setCommentMessage("پاسخ شما ثبت شد و در انتظار تایید مدیر است.");
    await loadComments();
  }

  return (
    <div className="rounded-2xl border border-slate-100 bg-white">
      <div className="flex gap-1 overflow-x-auto border-b border-slate-100 px-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              if (tab.key === "ratings" && tab.key !== active) {
                setRatingLoading(true);
                void loadRating();
              }
              if (tab.key === "comments" && tab.key !== active) {
                setCommentsLoading(true);
                void loadComments();
              }
              setActive(tab.key);
            }}
            className={`relative shrink-0 px-4 py-3 text-sm font-medium transition ${
              active === tab.key
                ? "text-brand-700"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
            {active === tab.key && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand-600" />
            )}
          </button>
        ))}
      </div>

      <div className="p-5">
        {active === "specs" && (
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-100">
              {product.specs?.map((spec) => (
                <tr key={spec.label}>
                  <td className="w-40 py-3 align-top text-slate-400">
                    {spec.label}
                  </td>
                  <td className="py-3 text-slate-700">{spec.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {active === "intro" && (
          <p className="text-sm leading-8 text-slate-600">
            {product.description}
          </p>
        )}

        {active === "ratings" && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-6 rounded-xl bg-slate-50 p-5">
              <div className="text-center">
                <div className="text-3xl font-bold text-slate-800 font-num">
                  {ratingData.average.toLocaleString("fa-IR")}
                </div>
                <div className="text-amber-400">★★★★★</div>
                <div className="mt-1 text-xs text-slate-400 font-num">
                  از {ratingData.count.toLocaleString("fa-IR")} امتیاز
                </div>
              </div>
              <div className="min-w-64 flex-1">
                {ratingLoading ? (
                  <p className="text-sm text-slate-400">در حال دریافت...</p>
                ) : ratingData.canRate ? (
                  <>
                    <p className="mb-3 text-sm font-bold text-slate-700">
                      {ratingData.myRating
                        ? "ویرایش امتیاز شما"
                        : "به این محصول امتیاز دهید"}
                    </p>
                    <div className="flex items-center gap-1" dir="ltr">
                      {[1, 2, 3, 4, 5].map((value) => (
                        <button
                          key={value}
                          type="button"
                          onClick={() => setSelectedRating(value)}
                          className={`text-3xl ${
                            value <= selectedRating
                              ? "text-amber-400"
                              : "text-slate-200"
                          }`}
                          aria-label={`${value} ستاره`}
                        >
                          ★
                        </button>
                      ))}
                    </div>
                    <button
                      type="button"
                      disabled={ratingSubmitting}
                      onClick={submitRating}
                      className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-50"
                    >
                      {ratingSubmitting ? "در حال ثبت..." : "ثبت امتیاز"}
                    </button>
                  </>
                ) : (
                  <p className="text-sm leading-7 text-slate-500">
                    امتیازدهی فقط برای کاربرانی فعال است که خرید پرداخت‌شده‌ی این محصول را دارند.
                  </p>
                )}
                {ratingMessage && (
                  <p className="mt-3 text-xs text-slate-500">{ratingMessage}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {active === "comments" && (
          <div className="space-y-5">
            <form
              onSubmit={submitComment}
              className="space-y-3 rounded-xl border border-slate-100 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-sm font-bold text-slate-700">
                  ثبت دیدگاه یا پرسش
                </h3>
                <select
                  value={commentType}
                  onChange={(event) =>
                    setCommentType(event.target.value as "comment" | "question")
                  }
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs"
                >
                  <option value="comment">دیدگاه</option>
                  <option value="question">پرسش</option>
                </select>
              </div>
              <textarea
                value={commentText}
                onChange={(event) => setCommentText(event.target.value)}
                minLength={5}
                maxLength={2000}
                required
                placeholder={
                  commentType === "question"
                    ? "پرسش خود درباره محصول را بنویسید"
                    : "تجربه یا نظر خود را بنویسید"
                }
                className="min-h-24 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:border-brand-400"
              />
              <button
                type="submit"
                disabled={commentSubmitting}
                className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-60"
              >
                {commentSubmitting ? "در حال ثبت..." : "ثبت پیام"}
              </button>
              <p className="text-[11px] leading-6 text-slate-400">
                تمام پیام‌های کاربران پیش از انتشار بررسی می‌شوند.
              </p>
              {commentMessage && (
                <p className="text-xs text-slate-500">{commentMessage}</p>
              )}
            </form>

            {commentsLoading ? (
              <p className="text-sm text-slate-400">در حال دریافت گفتگوها...</p>
            ) : comments.length === 0 ? (
              <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                هنوز دیدگاه یا پرسشی برای این محصول منتشر نشده است.
              </p>
            ) : (
              <div className="space-y-4">
                {comments.map((comment) => (
                  <CommentCard
                    key={comment.id}
                    comment={comment}
                    replyingTo={replyingTo}
                    replyText={replyText}
                    submittingReply={submittingReply}
                    onReply={(id) => {
                      setReplyingTo(id);
                      setReplyText("");
                    }}
                    onReplyText={setReplyText}
                    onSubmitReply={submitReply}
                    onCancelReply={() => {
                      setReplyingTo(null);
                      setReplyText("");
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
