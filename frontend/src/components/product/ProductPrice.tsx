import { discountPercent, formatPrice, type Product } from "@/lib/products";

/** نشان درصد تخفیف — قرمز و فشرده، درصد پس از عدد */
export function DiscountBadge({ percent }: { percent: number }) {
  return (
    <span className="shrink-0 rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-bold leading-4 text-white font-num @min-[12rem]/card:text-[11px]">
      {percent.toLocaleString("fa-IR")}٪
    </span>
  );
}

/**
 * بلوک قیمت کارت محصول.
 *
 * چیدمان: سطر اول قیمت پیش از تخفیف با خط‌خوردگی، سطر دوم «نشان تخفیف +
 * قیمت نهایی + تومان». ارتفاع سطر اول همیشه رزرو می‌شود تا قیمتِ نهاییِ
 * کارت‌های یک ردیف — تخفیف‌دار یا بدون تخفیف — روی یک خط بنشیند.
 */
export default function ProductPrice({
  product,
  muted = false,
}: {
  product: Product;
  muted?: boolean;
}) {
  const percent = discountPercent(product);

  return (
    <div className="min-w-0">
      <div className="min-h-4">
        {percent > 0 && (
          <span
            className="block truncate text-[11px] leading-4 text-slate-400 line-through decoration-slate-300 font-num"
            aria-label={`قیمت پیش از تخفیف ${formatPrice(product.oldPrice!)} تومان`}
          >
            {formatPrice(product.oldPrice!)}
          </span>
        )}
      </div>

      <div className="flex min-w-0 items-baseline gap-1.5">
        {percent > 0 && <DiscountBadge percent={percent} />}
        <span
          className={`truncate text-[13px] font-bold tracking-tight font-num @min-[12rem]/card:text-base ${
            muted ? "text-slate-400" : "text-slate-800"
          }`}
        >
          {formatPrice(product.price)}
        </span>
        <span
          className={`shrink-0 text-[10px] font-medium @min-[12rem]/card:text-[11px] ${
            muted ? "text-slate-400" : "text-slate-500"
          }`}
        >
          تومان
        </span>
      </div>
    </div>
  );
}
