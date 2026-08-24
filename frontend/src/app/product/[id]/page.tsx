import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getProductDetailById,
  getProductBySlug,
  getCategories,
} from "@/lib/catalog";
import type { ProductDetail } from "@/lib/catalog";
import { breadcrumbSchema, fetchSeo, toMetadata } from "@/lib/seo";
import type { Product } from "@/lib/products";
import ProductGallery from "@/components/product/ProductGallery";
import BuyBox from "@/components/product/BuyBox";
import ProductTabs from "@/components/product/ProductTabs";
import ProductCard from "@/components/product/ProductCard";
import FavoriteButton from "@/components/product/FavoriteButton";
import CompareButton from "@/components/product/CompareButton";
import JsonLd from "@/components/seo/JsonLd";
import RecentlyViewedTracker from "@/components/product/RecentlyViewedTracker";

// موجودی و امتیاز لحظه‌ای از دیتابیس خوانده می‌شود
export const dynamic = "force-dynamic";

// پارامتر می‌تواند شناسه عددی یا نامک سئو باشد
async function resolveProduct(
  idOrSlug: string
): Promise<{ product: ProductDetail; related: Product[] } | null> {
  const numeric = Number(idOrSlug);
  if (Number.isInteger(numeric) && numeric > 0) {
    return getProductDetailById(numeric);
  }
  return getProductBySlug(idOrSlug);
}

// متاتگ‌های سئو از پنل سئو خوانده می‌شوند
export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const resolved = await resolveProduct(id);
  if (!resolved) return {};
  const seo = await fetchSeo("product", String(resolved.product.id));
  return toMetadata(seo);
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const resolved = await resolveProduct(id);
  if (!resolved) notFound();

  const { product, related } = resolved;
  const [seo, storefrontCategories] = await Promise.all([
    fetchSeo("product", String(product.id)),
    getCategories(),
  ]);
  const hasImages = Boolean(product.images?.length);
  const assignedCategories = product.categories?.length
    ? product.categories
    : product.categorySlug
      ? [{ slug: product.categorySlug, title: product.category }]
      : [];
  const visibleCategorySlugs = new Set(
    storefrontCategories.map((category) => category.slug)
  );
  const productCategories = assignedCategories.filter((category) =>
    visibleCategorySlugs.has(category.slug)
  );
  const breadcrumbCategory = productCategories[0];

  return (
    <div className="site-container py-4 sm:py-5">
      <RecentlyViewedTracker productId={product.id} />
      {/* اسکیمای JSON-LD (محصول + بردکرامب) از پنل سئو */}
      {seo?.schema && <JsonLd data={seo.schema} />}
      {seo?.site.breadcrumbsEnabled && (
        <JsonLd
          data={breadcrumbSchema(seo.site, [
            { name: "خانه", path: "/" },
            ...(breadcrumbCategory
              ? [
                  {
                    name: breadcrumbCategory.title,
                    path: `/category/${breadcrumbCategory.slug}`,
                  },
                ]
              : []),
            { name: product.title, path: `/product/${product.id}` },
          ])}
        />
      )}

      {/* مسیر راهنما (breadcrumb) */}
      <nav aria-label="مسیر صفحه" className="mb-4 flex min-w-0 flex-wrap items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        {breadcrumbCategory && (
          <>
            <span>/</span>
            <Link
              href={`/category/${breadcrumbCategory.slug}`}
              className="hover:text-brand-600"
            >
              {breadcrumbCategory.title}
            </Link>
          </>
        )}
        <span>/</span>
        <span className="min-w-0 break-words text-slate-600">{product.title}</span>
      </nav>

      {/* بخش اصلی: گالری / اطلاعات / خرید */}
      <div className="grid grid-cols-1 gap-6 rounded-2xl border border-slate-100 bg-white p-4 lg:grid-cols-12 lg:gap-8 lg:p-6 xl:p-8">
        {hasImages && (
          <div className="lg:col-span-4">
            <ProductGallery
              images={product.images ?? []}
              title={product.title}
            />
          </div>
        )}

        {/* اطلاعات محصول */}
        <div className={hasImages ? "lg:col-span-5" : "lg:col-span-8"}>
          <div className="mb-2 flex flex-col-reverse items-start gap-3 min-[390px]:flex-row min-[390px]:justify-between">
            <h1 className="min-w-0 break-words text-xl font-bold leading-8 text-slate-800 sm:text-2xl sm:leading-9">
              {product.title}
            </h1>
            <div className="flex shrink-0 items-center gap-2">
              <CompareButton product={product} />
              <FavoriteButton
                productId={product.id}
                productTitle={product.title}
              />
            </div>
          </div>
          {product.titleEn && (
            <p className="mb-4 text-sm text-slate-400" dir="ltr">
              {product.titleEn}
            </p>
          )}

          {/* امتیاز، برند و دسته */}
          <div className="mb-6 flex flex-wrap items-center gap-4 text-sm">
            <span className="flex items-center gap-1 text-slate-500">
              <span className="text-amber-400">★</span>
              <span className="font-num">
                {product.rating.toLocaleString("fa-IR")}
              </span>
              <span className="font-num text-slate-400">
                ({product.ratingCount.toLocaleString("fa-IR")} امتیاز)
              </span>
            </span>
            {product.brand && product.brand.isActive !== false && (
              <>
                <span className="text-slate-300">|</span>
                <Link
                  href={`/brand/${product.brand.slug}`}
                  className="font-medium text-brand-600 hover:underline"
                >
                  برند {product.brand.name}
                </Link>
              </>
            )}
            {product.brand?.isActive === false && (
              <>
                <span className="text-slate-300">|</span>
                <span className="font-medium text-slate-500">
                  برند {product.brand.name}
                </span>
              </>
            )}
            {productCategories.length > 0 && (
              <>
                <span className="text-slate-300">|</span>
                <span className="flex flex-wrap items-center gap-2">
                  {productCategories.map((category) => (
                    <Link
                      key={category.slug}
                      href={`/category/${category.slug}`}
                      className="text-brand-600 hover:underline"
                    >
                      {category.title}
                    </Link>
                  ))}
                </span>
              </>
            )}
          </div>

          {/* انتخاب رنگ */}
          {product.colors && (
            <div className="mb-6">
              <span className="mb-2.5 block text-sm text-slate-600">
                رنگ: {product.colors[0].name}
              </span>
              <div className="flex gap-2.5">
                {product.colors.map((c) => (
                  <span
                    key={c.name}
                    title={c.name}
                    className="h-9 w-9 rounded-full border-2 border-white shadow ring-1 ring-slate-200"
                    style={{ backgroundColor: c.hex }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* ویژگی‌های کلیدی */}
          <div className="rounded-xl bg-slate-50 p-4 sm:p-6">
            <h2 className="mb-4 text-base font-bold text-slate-700">
              ویژگی‌های کلیدی
            </h2>
            <ul className="space-y-3">
              {product.features?.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2.5 text-sm leading-6 text-slate-600"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* جعبه خرید */}
        <div className={hasImages ? "lg:col-span-3" : "lg:col-span-4"}>
          <BuyBox product={product} />
        </div>
      </div>

      {/* تب‌های مشخصات / معرفی / امتیاز / گفتگو */}
      <div className="mt-6">
        <ProductTabs key={product.id} product={product} />
      </div>

      {/* محصولات مرتبط */}
      {related.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-4 text-lg font-bold text-slate-800">
            محصولات مشابه
          </h2>
          <div className="grid grid-cols-2 items-stretch gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5">
            {related.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
