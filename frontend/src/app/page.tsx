import Link from "next/link";
import { getCategories, getProducts } from "@/lib/catalog";
import { fetchSeo, orgSchema, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import JsonLd from "@/components/seo/JsonLd";

// داده‌ها از دیتابیس خوانده می‌شوند؛ صفحه داینامیک است
export const dynamic = "force-dynamic";

// متاتگ‌های سئو از پنل سئو خوانده می‌شوند
export async function generateMetadata() {
  const seo = await fetchSeo("static", "/");
  return toMetadata(seo);
}

export default async function Home() {
  const [categories, { items: bestSellers }, { items: deals }, seo] =
    await Promise.all([
      getCategories(),
      // «پرفروش‌ترین‌ها» انتخاب دستی مدیر فروشگاه است، نه صرفاً آمار فروش/امتیاز
      getProducts({ bestSeller: true, sort: "featured", perPage: 8 }),
      getProducts({ onlyDiscounted: true, perPage: 6 }),
      fetchSeo("static", "/"),
    ]);
  const rootCategories = categories.filter(
    (category) => category.isTopLevel !== false
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* اسکیمای Organization (قابل کنترل از پنل سئو) */}
      {seo?.site.orgSchemaEnabled && <JsonLd data={orgSchema(seo.site)} />}

      {/* بنر اصلی */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-secondary-700 to-brand-600 px-6 py-12 text-white sm:px-12 sm:py-16">
        <div className="relative z-10 max-w-lg">
          <h1 className="mb-3 text-2xl font-bold leading-relaxed sm:text-3xl">
            هر آنچه برای کشاورزی نیاز دارید، یکجا
          </h1>
          <p className="mb-6 text-sm leading-7 text-brand-50 sm:text-base">
            از بیل و قیچی باغبانی تا سمپاش و اره‌موتوری؛ با ضمانت اصالت کالا و
            ارسال سریع به سراسر کشور.
          </p>
          <Link
            href="/category/garden-tools"
            className="inline-block rounded-xl bg-white px-6 py-3 text-sm font-bold text-brand-700 transition hover:bg-brand-50"
          >
            مشاهده محصولات
          </Link>
        </div>
        <span className="pointer-events-none absolute -left-6 bottom-0 text-[10rem] opacity-20 sm:opacity-30">
          🚜
        </span>
      </section>

      {/* دسته‌بندی‌ها */}
      <section className="mt-8">
        <h2 className="mb-4 text-lg font-bold text-slate-800">دسته‌بندی‌ها</h2>
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-8">
          {rootCategories.map((c) => (
            <Link
              key={c.slug}
              href={`/category/${c.slug}`}
              className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-slate-100 bg-white p-4 transition hover:border-brand-200 hover:shadow-sm"
            >
              {c.icon && (
                <span className="grid h-14 w-14 place-items-center rounded-full bg-brand-50">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={c.icon}
                    alt=""
                    className="h-9 w-9 object-contain"
                  />
                </span>
              )}
              <span className="text-center text-xs text-slate-600">
                {c.title}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* شگفت‌انگیزها */}
      {deals.length > 0 && (
        <section className="mt-10 overflow-hidden rounded-3xl bg-gradient-to-l from-accent-600 to-accent-400 p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-lg font-bold text-secondary-900">
              ⚡ پیشنهاد شگفت‌انگیز
            </h2>
            <Link
              href="/incredible"
              className="rounded-xl bg-secondary-900/10 px-4 py-2 text-xs font-medium text-secondary-900 backdrop-blur transition hover:bg-secondary-900/20"
            >
              مشاهده همه ←
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {deals.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}

      {/* پرفروش‌ترین‌ها — منتخب دستی مدیر فروشگاه */}
      {bestSellers.length > 0 && (
        <section className="mt-10">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-800">🔥 پرفروش‌ترین‌ها</h2>
            <Link
              href="/best-sellers"
              className="text-sm text-brand-600 transition hover:text-brand-700"
            >
              مشاهده همه ←
            </Link>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {bestSellers.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
