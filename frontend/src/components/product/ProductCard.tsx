import Link from "next/link";
import { formatPrice, type Product } from "@/lib/products";

export default function ProductCard({ product }: { product: Product }) {
  const discount = product.oldPrice
    ? Math.round((1 - product.price / product.oldPrice) * 100)
    : 0;

  return (
    <Link
      href={`/product/${product.id}`}
      className="group flex h-full flex-col rounded-2xl border border-slate-100 bg-white p-3 transition hover:border-brand-200 hover:shadow-md"
    >
      {/* تصویر */}
      <div className="relative mb-3 grid aspect-square place-items-center overflow-hidden rounded-xl bg-slate-50 text-6xl">
        {product.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.image}
            alt={product.title}
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          product.emoji
        )}
        {product.badge && (
          <span className="absolute right-2 top-2 rounded-lg bg-brand-600 px-2 py-1 text-[11px] font-bold text-white">
            {product.badge}
          </span>
        )}
      </div>

      {/* عنوان */}
      <h3 className="mb-2 line-clamp-2 min-h-[2.5rem] text-sm leading-6 text-slate-700 group-hover:text-brand-700">
        {product.title}
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
      <div className="mt-auto flex items-end justify-between">
        <div>
          {product.oldPrice && (
            <div className="flex items-center gap-1">
              <span className="rounded-md bg-red-50 px-1.5 py-0.5 text-[11px] font-bold text-red-500 font-num">
                ٪{discount.toLocaleString("fa-IR")}
              </span>
              <span className="text-xs text-slate-300 line-through font-num">
                {formatPrice(product.oldPrice)}
              </span>
            </div>
          )}
          <div className="mt-1 flex items-baseline gap-1">
            <span className="text-base font-bold text-slate-800 font-num">
              {formatPrice(product.price)}
            </span>
            <span className="text-xs text-slate-400">تومان</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
