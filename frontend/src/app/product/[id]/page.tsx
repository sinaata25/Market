import Link from "next/link";
import { notFound } from "next/navigation";
import { getProductById, getRelatedProducts } from "@/lib/catalog";
import ProductGallery from "@/components/product/ProductGallery";
import BuyBox from "@/components/product/BuyBox";
import ProductTabs from "@/components/product/ProductTabs";
import ProductCard from "@/components/product/ProductCard";

// موجودی و امتیاز لحظه‌ای از دیتابیس خوانده می‌شود
export const dynamic = "force-dynamic";

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const productId = Number(id);
  if (!Number.isInteger(productId)) notFound();

  const product = await getProductById(productId);
  if (!product) notFound();

  const related = await getRelatedProducts(product.id);

  return (
    <div className="mx-auto max-w-7xl px-4 py-5">
      {/* مسیر راهنما (breadcrumb) */}
      <nav className="mb-4 flex flex-wrap items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="hover:text-brand-600">{product.category}</span>
        <span>/</span>
        <span className="text-slate-600">{product.title}</span>
      </nav>

      {/* بخش اصلی: گالری / اطلاعات / خرید */}
      <div className="grid grid-cols-1 gap-6 rounded-2xl border border-slate-100 bg-white p-4 lg:grid-cols-12 lg:p-6">
        {/* گالری */}
        <div className="lg:col-span-4">
          <ProductGallery emoji={product.emoji} />
        </div>

        {/* اطلاعات محصول */}
        <div className="lg:col-span-5">
          <h1 className="mb-1 text-lg font-bold leading-8 text-slate-800">
            {product.title}
          </h1>
          {product.titleEn && (
            <p className="mb-3 text-xs text-slate-400" dir="ltr">
              {product.titleEn}
            </p>
          )}

          {/* امتیاز و دسته */}
          <div className="mb-5 flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1 text-slate-500">
              <span className="text-amber-400">★</span>
              <span className="font-num">
                {product.rating.toLocaleString("fa-IR")}
              </span>
              <span className="font-num text-slate-400">
                ({product.ratingCount.toLocaleString("fa-IR")} دیدگاه)
              </span>
            </span>
            <span className="text-slate-300">|</span>
            <Link href="#" className="text-brand-600">
              {product.category}
            </Link>
          </div>

          {/* انتخاب رنگ */}
          {product.colors && (
            <div className="mb-5">
              <span className="mb-2 block text-sm text-slate-600">
                رنگ: {product.colors[0].name}
              </span>
              <div className="flex gap-2">
                {product.colors.map((c) => (
                  <span
                    key={c.name}
                    title={c.name}
                    className="h-8 w-8 rounded-full border-2 border-white shadow ring-1 ring-slate-200"
                    style={{ backgroundColor: c.hex }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ویژگی‌های کلیدی */}
          <div className="rounded-xl bg-slate-50 p-4">
            <h2 className="mb-3 text-sm font-bold text-slate-700">
              ویژگی‌های کلیدی
            </h2>
            <ul className="space-y-2">
              {product.features?.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2 text-sm text-slate-600"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* جعبه خرید */}
        <div className="lg:col-span-3">
          <BuyBox product={product} />
        </div>
      </div>

      {/* تب‌های مشخصات / معرفی / دیدگاه */}
      <div className="mt-6">
        <ProductTabs product={product} />
      </div>

      {/* محصولات مرتبط */}
      {related.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-4 text-lg font-bold text-slate-800">
            محصولات مشابه
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {related.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
