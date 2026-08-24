import Image from "next/image";
import Link from "next/link";
import { formatPrice, type Product } from "@/lib/products";
import AddToCartButton from "@/components/product/AddToCartButton";
import CompareButton from "@/components/product/CompareButton";
import FavoriteButton from "@/components/product/FavoriteButton";

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

function ProductRating({ product }: { product: Product }) {
  if (product.ratingCount < 1 || product.rating <= 0) return null;

  const rating = product.rating.toLocaleString("fa-IR", {
    maximumFractionDigits: 1,
  });
  const count = product.ratingCount.toLocaleString("fa-IR");

  return (
    <span
      dir="ltr"
      aria-label={`امتیاز ${rating} از ۵، بر پایه ${count} رأی`}
      className="mr-auto inline-flex shrink-0 items-center gap-1 text-[11px] text-slate-400 font-num"
    >
      <span className="font-medium text-slate-600">{rating}</span>
      <svg
        viewBox="0 0 20 20"
        aria-hidden="true"
        className="h-3.5 w-3.5 fill-amber-400 text-amber-400"
      >
        <path d="m10 1.7 2.46 4.98 5.5.8-3.98 3.88.94 5.48L10 14.25l-4.92 2.59.94-5.48L2.04 7.48l5.5-.8L10 1.7Z" />
      </svg>
      <span aria-hidden="true">({count})</span>
    </span>
  );
}

function ProductPrice({
  product,
  outOfStock,
}: {
  product: Product;
  outOfStock: boolean;
}) {
  const hasDiscount =
    typeof product.oldPrice === "number" && product.oldPrice > product.price;
  const discount = hasDiscount
    ? Math.round((1 - product.price / product.oldPrice!) * 100)
    : 0;

  return (
    <div className={`min-w-0 flex-1 ${outOfStock ? "opacity-60" : ""}`}>
      <div className="mb-0.5 flex min-h-5 min-w-0 items-center justify-end gap-1.5">
        {hasDiscount && (
          <>
            <span className="shrink-0 rounded-md bg-accent-500 px-1.5 py-0.5 text-[10px] font-bold text-secondary-900 font-num">
              ٪{discount.toLocaleString("fa-IR")}
            </span>
            <span className="min-w-0 truncate text-[11px] text-slate-400 line-through decoration-slate-300 font-num">
              {formatPrice(product.oldPrice!)}
            </span>
          </>
        )}
      </div>
      <div
        aria-label={`قیمت ${formatPrice(product.price)} تومان`}
        className="flex min-w-0 items-baseline justify-end gap-1 whitespace-nowrap"
      >
        <span className="text-[13px] font-bold tracking-tight text-slate-800 font-num @min-[12rem]/card:text-base">
          {formatPrice(product.price)}
        </span>
        <span className="text-[10px] font-medium text-slate-500 @min-[12rem]/card:text-[11px]">
          تومان
        </span>
      </div>
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
      <div className="relative mb-2.5 aspect-square w-full overflow-hidden rounded-xl bg-slate-50 sm:mb-3">
        {product.image ? (
          <Image
            src={product.image}
            alt={product.title}
            fill
            sizes="(max-width: 639px) 50vw, (max-width: 1023px) 33vw, (max-width: 1279px) 25vw, 20rem"
            className={`object-contain p-2 transition-transform duration-300 motion-safe:group-hover:scale-[1.025] @min-[12rem]/card:p-3 ${
              outOfStock ? "opacity-60 grayscale-[25%]" : ""
            }`}
          />
        ) : (
          <ProductImageFallback title={product.title} />
        )}

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

        {outOfStock && (
          <span className="pointer-events-none absolute bottom-1.5 right-1.5 z-20 inline-flex items-center gap-1 rounded-lg bg-slate-800/90 px-2 py-1 text-[10px] font-bold text-white shadow-sm sm:bottom-2 sm:right-2 sm:text-[11px]">
            <span className="h-1.5 w-1.5 rounded-full border border-white" />
            ناموجود
          </span>
        )}
      </div>

      <div className="mb-1 min-h-4 min-w-0">
        {product.brand && (
          <span className="block truncate text-[10px] font-medium text-brand-700 @min-[12rem]/card:text-[11px]">
            {product.brand.name}
          </span>
        )}
      </div>

      <h3 className="mb-1.5 line-clamp-2 min-h-12 text-[13px] font-medium leading-6 text-slate-700 transition-colors group-hover:text-brand-800 @min-[12rem]/card:text-sm">
        <Link
          href={`/product/${product.id}`}
          className="focus-visible:outline-none after:absolute after:inset-0 after:z-10 after:rounded-2xl after:content-[''] focus-visible:after:ring-2 focus-visible:after:ring-brand-500 focus-visible:after:ring-offset-2"
        >
          {product.title}
        </Link>
      </h3>

      <div className="mb-2 flex min-h-5 min-w-0 items-center gap-2">
        {outOfStock ? (
          <span className="inline-flex min-w-0 items-center gap-1 text-[10px] font-medium text-slate-500 @min-[12rem]/card:text-[11px]">
            <span
              aria-hidden="true"
              className="h-1.5 w-1.5 shrink-0 rounded-full border border-slate-500"
            />
            ناموجود در انبار
          </span>
        ) : lowStock ? (
          <span className="truncate text-[10px] font-medium text-red-600 font-num @min-[12rem]/card:text-[11px]">
            تنها {product.stock!.toLocaleString("fa-IR")} عدد
          </span>
        ) : null}
        <ProductRating product={product} />
      </div>

      <div className="mt-auto flex min-w-0 flex-col gap-2 border-t border-slate-100 pt-2.5 @min-[12rem]/card:flex-row @min-[12rem]/card:items-end @min-[12rem]/card:justify-between">
        <ProductPrice product={product} outOfStock={outOfStock} />
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
