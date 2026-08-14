import Link from "next/link";
import { formatPrice, type Product } from "@/lib/products";
import AddToCartButton from "@/components/product/AddToCartButton";

export default function ProductCard({ product }: { product: Product }) {
  const discount = product.oldPrice
    ? Math.round((1 - product.price / product.oldPrice) * 100)
    : 0;

  return (
    <article className="@container/card group relative flex h-full flex-col rounded-2xl border border-slate-100 bg-white p-3 transition hover:border-brand-200 hover:shadow-md focus-within:border-brand-300">
      {product.image && (
        <div className="relative mb-3 aspect-square overflow-hidden rounded-xl bg-slate-50">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={product.image}
            alt={product.title}
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            loading="lazy"
          />
          {product.badge && (
            <span className="absolute right-2 top-2 rounded-lg bg-brand-600 px-2 py-1 text-[11px] font-bold text-white">
              {product.badge}
            </span>
          )}
        </div>
      )}
      {!product.image && product.badge && (
        <span className="mb-3 self-start rounded-lg bg-brand-600 px-2 py-1 text-[11px] font-bold text-white">
          {product.badge}
        </span>
      )}

      {/* عنوان */}
      {product.brand && (
        <span className="mb-1 text-[11px] font-medium text-brand-600">
          {product.brand.name}
        </span>
      )}
      <h3 className="mb-2 line-clamp-2 min-h-[2.5rem] text-sm leading-6 text-slate-700 group-hover:text-brand-700">
        <Link
          href={`/product/${product.id}`}
          className="after:absolute after:inset-0 after:rounded-2xl after:content-[''] focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-brand-500 focus-visible:after:ring-offset-2"
        >
          {product.title}
        </Link>
      </h3>

      {/* امتیاز */}
      <div className="mb-3 flex items-center gap-1 text-xs text-slate-400">
        <span className="text-amber-400">★</span>
        <span className="font-num text-slate-600">
          {product.rating.toLocaleString("fa-IR")}
        </span>
        <span className="font-num">
          ({product.ratingCount.toLocaleString("fa-IR")})
        </span>
      </div>

      {/* قیمت */}
      <div className="mt-auto flex flex-col items-end gap-2 @min-[11rem]/card:flex-row @min-[11rem]/card:justify-between">
        <div className="w-full min-w-0 @min-[11rem]/card:w-auto">
          {product.oldPrice && (
            <div className="flex items-center gap-1">
              <span className="rounded-md bg-accent-50 px-1.5 py-0.5 text-[11px] font-bold text-accent-700 font-num">
                ٪{discount.toLocaleString("fa-IR")}
              </span>
              <span className="text-xs text-slate-300 line-through font-num">
                {formatPrice(product.oldPrice)}
              </span>
            </div>
          )}
          <div className="mt-1 flex flex-col items-start @min-[11rem]/card:flex-row @min-[11rem]/card:items-baseline @min-[11rem]/card:gap-1">
            <span className="text-sm font-bold text-slate-800 font-num @min-[11rem]/card:text-base">
              {formatPrice(product.price)}
            </span>
            <span className="text-[10px] text-slate-400 @min-[11rem]/card:text-xs">
              تومان
            </span>
          </div>
        </div>
        <AddToCartButton
          productId={product.id}
          productTitle={product.title}
          stock={product.stock}
        />
      </div>
    </article>
  );
}
