import type { Product } from "@/lib/products";

/**
 * امتیاز فشرده به شکل «۴.۶ ★».
 *
 * نبودِ امتیاز یعنی چیزی نمایش داده نمی‌شود (رفتار قبلی پروژه) — هیچ مقدار
 * ساختگی جای امتیاز واقعی را نمی‌گیرد. تعداد رأی‌ها فقط در کارت‌های عریض‌تر
 * دیده می‌شود تا در موبایل جای قیمت را تنگ نکند.
 */
export default function ProductRating({
  product,
  className = "",
}: {
  product: Product;
  className?: string;
}) {
  if (product.ratingCount < 1 || product.rating <= 0) return null;

  const rating = product.rating.toLocaleString("fa-IR", {
    maximumFractionDigits: 1,
  });
  const count = product.ratingCount.toLocaleString("fa-IR");

  return (
    <span
      dir="ltr"
      aria-label={`امتیاز ${rating} از ۵، بر پایه ${count} رأی`}
      className={`inline-flex shrink-0 items-center gap-1 text-[11px] text-slate-400 font-num ${className}`}
    >
      <span className="font-medium text-slate-600">{rating}</span>
      <svg
        viewBox="0 0 20 20"
        aria-hidden="true"
        className="h-3.5 w-3.5 fill-amber-400 text-amber-400"
      >
        <path d="m10 1.7 2.46 4.98 5.5.8-3.98 3.88.94 5.48L10 14.25l-4.92 2.59.94-5.48L2.04 7.48l5.5-.8L10 1.7Z" />
      </svg>
      <span aria-hidden="true" className="hidden @min-[12rem]/card:inline">
        ({count})
      </span>
    </span>
  );
}
