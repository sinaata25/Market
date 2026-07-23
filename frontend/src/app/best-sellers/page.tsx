import Link from "next/link";
import { getCategories, getProducts } from "@/lib/catalog";
import { formatPrice } from "@/lib/products";
import { fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";

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
    getProducts({
      sort: "popular",
      perPage: 50,
      categorySlug: activeCategory,
    }),
  ]);

  const top3 = items.slice(0, 3);
  const rest = items.slice(3);
  const activeTitle = categories.find((c) => c.slug === activeCategory)?.title;

  function url(slug?: string) {
    return slug ? `/best-sellers?category=${slug}` : "/best-sellers";
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
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
              محبوب‌ترین کالاها بر اساس نظر و خرید مشتریان
            </p>
          </div>
        </div>
      </section>

      {/* فیلتر دسته‌بندی */}
      <div className="mb-6 flex flex-wrap gap-2">
        <Link
          href={url()}
          className={`rounded-full border px-4 py-1.5 text-xs transition ${
            !activeCategory
              ? "border-brand-500 bg-brand-600 font-medium text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
          }`}
        >
          همه دسته‌ها
        </Link>
        {categories.map((c) => (
          <Link
            key={c.slug}
            href={url(c.slug)}
            className={`rounded-full border px-4 py-1.5 text-xs transition ${
              activeCategory === c.slug
                ? "border-brand-500 bg-brand-600 font-medium text-white"
                : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
            }`}
          >
            {c.emoji} {c.title}
          </Link>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">📦</span>
          <h2 className="mb-2 font-bold text-slate-700">
            کالایی در این دسته یافت نشد
          </h2>
          <Link
            href={url()}
            className="mt-4 inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مشاهده همه پرفروش‌ها
          </Link>
        </div>
      ) : (
        <>
          {/* سکوی سه‌تایی */}
          <section className="mb-8">
            <h2 className="mb-4 text-base font-bold text-slate-800">
              🏅 سه محصول برتر
            </h2>
            <div className="grid gap-3 sm:grid-cols-3">
              {top3.map((p, i) => (
                <Link
                  key={p.id}
                  href={`/product/${p.id}`}
                  className="group relative flex items-center gap-4 overflow-hidden rounded-2xl border border-slate-100 bg-white p-4 transition hover:border-amber-200 hover:shadow-md"
                >
                  <span className="absolute left-3 top-3 text-2xl">
                    {MEDALS[i]}
                  </span>
                  <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-xl bg-slate-50 text-3xl">
                    {p.image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={p.image}
                        alt={p.title}
                        className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                      />
                    ) : (
                      p.emoji
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="mb-2 line-clamp-2 text-xs leading-5 text-slate-700 group-hover:text-brand-700">
                      {p.title}
                    </h3>
                    <div className="mb-1.5 flex items-center gap-1 text-[11px] text-slate-400">
                      <span className="text-amber-400">★</span>
                      <span className="font-num text-slate-600">
                        {p.rating.toLocaleString("fa-IR")}
                      </span>
                      <span className="font-num">
                        ({p.ratingCount.toLocaleString("fa-IR")} دیدگاه)
                      </span>
                    </div>
                    <p className="text-sm font-bold text-slate-800 font-num">
                      {formatPrice(p.price)}
                      <span className="mr-1 text-[11px] font-normal text-slate-400">
                        تومان
                      </span>
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* بقیه محصولات */}
          {rest.length > 0 && (
            <section>
              <h2 className="mb-4 text-base font-bold text-slate-800">
                سایر محصولات پرفروش
              </h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
                {rest.map((p) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
