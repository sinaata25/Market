import Link from "next/link";
import { getCategories, getProducts } from "@/lib/catalog";
import { fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import ProductGrid from "@/components/product/ProductGrid";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const seo = await fetchSeo("static", "/best-sellers");
  return toMetadata(seo);
}

const MEDALS = ["🥇", "🥈", "🥉"];

export default async function BestSellersPage({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const sp = await searchParams;
  const activeCategory = sp.category;

  const [categories, { items }] = await Promise.all([
    getCategories(),
    // «پرفروش‌ترین‌ها» انتخاب دستی مدیر فروشگاه است، نه صرفاً آمار فروش/امتیاز
    getProducts({
      bestSeller: true,
      sort: "featured",
      perPage: 50,
      categorySlug: activeCategory,
    }),
  ]);

  const top3 = items.slice(0, 3);
  const rest = items.slice(3);
  const activeTitle = categories.find((c) => c.slug === activeCategory)?.title;
  const rootCategories = categories.filter(
    (category) => category.isTopLevel !== false
  );

  function url(slug?: string) {
    return slug ? `/best-sellers?category=${slug}` : "/best-sellers";
  }

  return (
    <div className="site-shell py-6">
      {/* مسیر راهنما */}
      <nav className="mb-4 flex items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="text-slate-600">پرفروش‌ترین‌ها</span>
      </nav>

      {/* هدر */}
      <section className="mb-6 overflow-hidden rounded-3xl bg-gradient-to-l from-amber-500 to-orange-400 px-6 py-6">
        <div className="flex items-center gap-4">
          <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-white/20 text-4xl backdrop-blur">
            🏆
          </span>
          <div>
            <h1 className="text-xl font-bold text-white">
              پرفروش‌ترین‌ها
              {activeTitle && (
                <span className="text-base font-normal"> — {activeTitle}</span>
              )}
            </h1>
            <p className="mt-1 text-xs text-white/90">
              منتخب فروشگاه؛ کالاهایی که تیم گروه صنعتی توانا برایتان برگزیده است
            </p>
          </div>
        </div>
      </section>

      {/* فیلتر دسته‌بندی */}
      <div className="mb-6 flex flex-wrap gap-2">
        <Link
          href={url()}
          className={`inline-flex min-h-11 items-center rounded-full border px-4 py-1.5 text-xs transition sm:min-h-0 ${
            !activeCategory
              ? "border-brand-500 bg-brand-600 font-medium text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
          }`}
        >
          همه دسته‌ها
        </Link>
        {rootCategories.map((c) => (
          <Link
            key={c.slug}
            href={url(c.slug)}
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-full border px-4 py-1.5 text-xs transition sm:min-h-0 ${
              activeCategory === c.slug
                ? "border-brand-500 bg-brand-600 font-medium text-white"
                : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
            }`}
          >
            {c.icon && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={c.icon}
                alt=""
                className="h-4 w-4 shrink-0 object-contain"
              />
            )}
            {c.title}
          </Link>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">📦</span>
          <h2 className="mb-2 font-bold text-slate-700">
            {activeCategory
              ? "در این دسته هنوز محصولی به پرفروش‌ترین‌ها اضافه نشده است"
              : "هنوز محصولی به پرفروش‌ترین‌ها اضافه نشده است"}
          </h2>
          {activeCategory && (
            <Link
              href={url()}
              className="mt-4 inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
            >
              مشاهده همه پرفروش‌ها
            </Link>
          )}
        </div>
      ) : (
        <>
          {/* سکوی سه‌تایی */}
          <section className="mb-8">
            <h2 className="mb-4 text-base font-bold text-slate-800">
              🏅 سه محصول برتر
            </h2>
            {/* همان کارت محصول سایت + مدال رتبه؛ جای مدال با دکمه‌ی
                علاقه‌مندی تداخل نکند، پس در این بخش نمایش داده نمی‌شود */}
            <div className="grid grid-cols-2 items-stretch gap-2.5 sm:gap-3 md:grid-cols-3">
              {top3.map((p, i) => (
                <div key={p.id} className="relative">
                  <span
                    aria-label={`رتبه ${(i + 1).toLocaleString("fa-IR")}`}
                    className="absolute left-1.5 top-1.5 z-30 text-2xl drop-shadow-sm sm:left-2 sm:top-2"
                  >
                    {MEDALS[i]}
                  </span>
                  <ProductCard product={p} showFavorite={false} />
                </div>
              ))}
            </div>
          </section>

          {/* بقیه محصولات */}
          {rest.length > 0 && (
            <section>
              <h2 className="mb-4 text-base font-bold text-slate-800">
                سایر محصولات پرفروش
              </h2>
              <ProductGrid>
                {rest.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </ProductGrid>
            </section>
          )}
        </>
      )}
    </div>
  );
}
