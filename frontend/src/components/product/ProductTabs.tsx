"use client";

import { useEffect, useState } from "react";
import type { Product } from "@/lib/products";
import { api } from "@/lib/client-api";

const tabs = [
  { key: "specs", label: "مشخصات" },
  { key: "intro", label: "معرفی" },
  { key: "reviews", label: "دیدگاه‌ها" },
] as const;

type TabKey = (typeof tabs)[number]["key"];

type Review = {
  id: number;
  rating: number;
  text: string;
  createdAt: string;
  author: string;
};

export default function ProductTabs({ product }: { product: Product }) {
  const [active, setActive] = useState<TabKey>("specs");
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [reviewText, setReviewText] = useState("");
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewMessage, setReviewMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (active !== "reviews") return;
    api
      .get<{ reviews: Review[] }>(`/api/products/${product.id}/reviews`)
      .then((res) => {
        if (res.ok && res.data) setReviews(res.data.reviews);
        else setReviewMessage(res.error ?? "خطا در دریافت دیدگاه‌ها");
      })
      .finally(() => setReviewsLoading(false));
  }, [active, product.id]);

  async function submitReview(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setReviewMessage("");
    const res = await api.post<{
      review: { id: number; isPublished: boolean };
    }>(
      `/api/products/${product.id}/reviews`,
      { rating: reviewRating, text: reviewText }
    );
    setSubmitting(false);
    if (!res.ok) {
      setReviewMessage(
        res.status === 401
          ? "برای ثبت دیدگاه ابتدا وارد حساب خود شوید"
          : (res.error ?? "خطا در ثبت دیدگاه")
      );
      return;
    }
    setReviewText("");
    setReviewMessage("دیدگاه شما ثبت شد و پس از تایید مدیر منتشر می‌شود.");
  }

  return (
    <div className="rounded-2xl border border-slate-100 bg-white">
      {/* سر تب‌ها */}
      <div className="flex gap-1 border-b border-slate-100 px-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => {
              if (t.key === "reviews") setReviewsLoading(true);
              setActive(t.key);
            }}
            className={`relative px-4 py-3 text-sm font-medium transition ${
              active === t.key
                ? "text-brand-700"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
            {active === t.key && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand-600" />
            )}
          </button>
        ))}
      </div>

      <div className="p-5">
        {active === "specs" && (
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-100">
              {product.specs?.map((s) => (
                <tr key={s.label}>
                  <td className="w-40 py-3 align-top text-slate-400">
                    {s.label}
                  </td>
                  <td className="py-3 text-slate-700">{s.value}</td>
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

        {active === "reviews" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-slate-800 font-num">
                  {product.rating.toLocaleString("fa-IR")}
                </div>
                <div className="text-amber-400">★★★★★</div>
                <div className="mt-1 text-xs text-slate-400 font-num">
                  از {product.ratingCount.toLocaleString("fa-IR")} دیدگاه
                </div>
              </div>
              <p className="flex-1 text-sm leading-7 text-slate-500">
                خریداران از کیفیت و عملکرد این محصول رضایت بالایی داشته‌اند. شما
                هم می‌توانید پس از خرید، دیدگاه خود را ثبت کنید.
              </p>
            </div>

            <form
              onSubmit={submitReview}
              className="space-y-3 rounded-xl border border-slate-100 p-4"
            >
              <h3 className="text-sm font-bold text-slate-700">ثبت دیدگاه</h3>
              <label className="block text-xs text-slate-500">
                امتیاز
                <select
                  value={reviewRating}
                  onChange={(e) => setReviewRating(Number(e.target.value))}
                  className="mt-1 block rounded-lg border border-slate-200 bg-white px-3 py-2"
                >
                  {[5, 4, 3, 2, 1].map((rating) => (
                    <option key={rating} value={rating}>
                      {rating.toLocaleString("fa-IR")} ستاره
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                minLength={5}
                maxLength={1000}
                required
                placeholder="تجربه خود از این محصول را بنویسید"
                className="min-h-24 w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:border-brand-400"
              />
              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-brand-600 px-4 py-2 text-xs font-bold text-white disabled:opacity-60"
              >
                {submitting ? "در حال ثبت..." : "ثبت دیدگاه"}
              </button>
              {reviewMessage && (
                <p className="text-xs text-slate-500">{reviewMessage}</p>
              )}
            </form>

            {reviewsLoading ? (
              <p className="text-sm text-slate-400">در حال دریافت دیدگاه‌ها...</p>
            ) : reviews.length === 0 ? (
              <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                هنوز دیدگاهی برای این محصول ثبت نشده است.
              </p>
            ) : (
              reviews.map((review) => (
                <article
                  key={review.id}
                  className="rounded-xl border border-slate-100 p-4"
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">
                      {review.author}
                    </span>
                    <span
                      className="text-xs text-amber-400"
                      aria-label={`${review.rating} از ۵ ستاره`}
                    >
                      {"★".repeat(review.rating)}
                      <span className="text-slate-200">
                        {"★".repeat(5 - review.rating)}
                      </span>
                    </span>
                  </div>
                  <p className="text-sm leading-7 text-slate-500">
                    {review.text}
                  </p>
                </article>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
