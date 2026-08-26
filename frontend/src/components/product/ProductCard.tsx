import Image from "next/image";
import Link from "next/link";
import type { Product } from "@/lib/products";
import AddToCartButton from "@/components/product/AddToCartButton";
import CompareButton from "@/components/product/CompareButton";
import FavoriteButton from "@/components/product/FavoriteButton";
import ProductPrice from "@/components/product/ProductPrice";
import ProductRating from "@/components/product/ProductRating";

type ProductCardProps = {
  product: Product;
  showFavorite?: boolean;
  onFavoriteChange?: (favorited: boolean) => void;
};

function ProductImageFallback({ title }: { title: string }) {
  return (
    <div
      role="img"
      aria-label={`تصویری برای ${title} موجود نیست`}
      className="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-b from-slate-50 to-brand-50/60 px-3 text-center text-slate-400"
    >
      <svg
        viewBox="0 0 48 48"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className="h-10 w-10 text-brand-300 @min-[11rem]/card:h-12 @min-[11rem]/card:w-12"
      >
        <path d="M9 14.5 24 7l15 7.5v19L24 41 9 33.5v-19Z" />
        <path d="m9 14.5 15 7.7 15-7.7M24 22.2V41" />
        <path d="m17 10.5 15 7.6" />
      </svg>
      <span className="text-[10px] leading-4 @min-[11rem]/card:text-[11px]">
        تصویر محصول موجود نیست
      </span>
    </div>
  );
}

export default function ProductCard({
  product,
  showFavorite = true,
  onFavoriteChange,
}: ProductCardProps) {
  const outOfStock = product.stock === 0;
  const lowStock =
    typeof product.stock === "number" &&
    product.stock > 0 &&
    product.stock <= 5;

  return (
    <article className="@container/card group relative isolate flex h-full min-w-0 flex-col rounded-2xl border border-slate-200/80 bg-white p-2 transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-[0_10px_30px_-18px_rgba(35,57,28,0.5)] focus-within:border-brand-300 focus-within:shadow-[0_10px_30px_-18px_rgba(35,57,28,0.5)] motion-reduce:transform-none sm:p-3">
      {/* تصویر — نسبت ثابت ۱:۱ و object-contain: بدون تغییر چیدمان هنگام
          بارگذاری و بدون کشیدگی برای تصاویر عمودی یا افقی */}
      <div className="relative mb-2.5 aspect-square w-full overflow-hidden rounded-xl bg-slate-50 sm:mb-3">
        {product.image ? (
          <Image
            src={product.image}
            alt={product.title}
            fill
            sizes="(max-width: 639px) 50vw, (max-width: 1023px) 33vw, (max-width: 1279px) 25vw, 15rem"
            className={`object-contain p-2 transition-transform duration-300 motion-safe:group-hover:scale-[1.025] @min-[12rem]/card:p-3 ${
              outOfStock ? "opacity-60 grayscale-[25%]" : ""
            }`}
          />
        ) : (
          <ProductImageFallback title={product.title} />
        )}

        {/* برچسب متنی محصول — تنها حالتِ برچسبی که بک‌اند پشتیبانی می‌کند */}
        {product.badge && (
          <span className="pointer-events-none absolute right-1.5 top-1.5 z-20 max-w-[calc(100%-2.75rem)] truncate rounded-lg bg-brand-700/95 px-2 py-1 text-[10px] font-bold text-white shadow-sm sm:right-2 sm:top-2 sm:text-[11px]">
            {product.badge}
          </span>
        )}

        {showFavorite && (
          <div className="absolute left-1.5 top-1.5 z-20 sm:left-2 sm:top-2">
            <FavoriteButton
              productId={product.id}
              productTitle={product.title}
              variant="card"
              onChange={onFavoriteChange}
            />
          </div>
        )}

        {/* ناموجودی هم با متن و هم با نشانه دیده می‌شود، نه فقط با رنگ */}
        {outOfStock && (
          <span className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-center justify-center gap-1 bg-slate-800/85 py-1 text-[10px] font-bold text-white sm:text-[11px]">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 rounded-full border border-white"
            />
            ناموجود
          </span>
        )}
      </div>

      {/* برند — ثانویه، بالای عنوان */}
      <div className="mb-1 min-h-4 min-w-0">
        {product.brand && (
          <span className="block truncate text-[10px] font-medium text-brand-700 @min-[12rem]/card:text-[11px]">
            {product.brand.name}
          </span>
        )}
      </div>

      {/* عنوان — همیشه دو سطر تا کارت‌های یک ردیف هم‌تراز بمانند */}
      <h3 className="line-clamp-2 min-h-10 text-[13px] font-medium leading-5 text-slate-700 transition-colors group-hover:text-brand-800 @min-[12rem]/card:text-sm">
        <Link
          href={`/product/${product.id}`}
          className="focus-visible:outline-none after:absolute after:inset-0 after:z-10 after:rounded-2xl after:content-[''] focus-visible:after:ring-2 focus-visible:after:ring-brand-500 focus-visible:after:ring-offset-2"
        >
          {product.title}
        </Link>
      </h3>

      {/* امتیاز و موجودی — ثانویه نسبت به عنوان و قیمت */}
      <div className="mt-1.5 flex min-h-5 min-w-0 items-center gap-2">
        <ProductRating product={product} />
        {outOfStock ? (
          <span className="ms-auto inline-flex min-w-0 items-center gap-1 truncate text-[10px] font-medium text-slate-500 @min-[12rem]/card:text-[11px]">
            ناموجود در انبار
          </span>
        ) : lowStock ? (
          <span className="ms-auto truncate text-[10px] font-medium text-red-600 font-num @min-[12rem]/card:text-[11px]">
            تنها {product.stock!.toLocaleString("fa-IR")} عدد
          </span>
        ) : null}
      </div>

      {/* قیمت و کنش‌ها — پایین کارت، بیشترین وزن بصری */}
      <div className="mt-auto flex min-w-0 flex-col gap-2 border-t border-slate-100 pt-2.5 @min-[12rem]/card:flex-row @min-[12rem]/card:items-end @min-[12rem]/card:justify-between">
        <ProductPrice product={product} muted={outOfStock} />
        <div className="relative z-20 flex shrink-0 items-center gap-1.5 self-end">
          <CompareButton product={product} variant="card" />
          <AddToCartButton
            productId={product.id}
            productTitle={product.title}
            stock={product.stock}
            variant="card"
          />
        </div>
      </div>
    </article>
  );
}
