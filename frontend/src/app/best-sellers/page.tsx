import Link from "next/link";
import { getCategories, getProducts } from "@/lib/catalog";
import { formatPrice } from "@/lib/products";
import { fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import AddToCartButton from "@/components/product/AddToCartButton";

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
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {top3.map((p, i) => (
                <article
                  key={p.id}
                  className="group relative flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-4 transition hover:border-amber-200 hover:shadow-md focus-within:border-amber-300 md:flex-col md:items-stretch lg:flex-row lg:items-center"
                >
                  <span className="absolute left-3 top-3 text-2xl">
                    {MEDALS[i]}
                  </span>
                  {p.image && (
                    <div className="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-slate-50 md:h-28 md:w-full lg:h-20 lg:w-20">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={p.image}
                        alt={p.title}
                        className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                      />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <h3 className="mb-2 line-clamp-2 text-xs leading-5 text-slate-700 group-hover:text-brand-700">
                      <Link
                        href={`/product/${p.id}`}
                        className="after:absolute after:inset-0 after:rounded-2xl after:content-[''] focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-amber-400 focus-visible:after:ring-offset-2"
                      >
                        {p.title}
                      </Link>
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
                    <div className="flex items-end justify-between gap-2">
                      <p className="text-sm font-bold text-slate-800 font-num">
                        {formatPrice(p.price)}
                        <span className="mr-1 text-[11px] font-normal text-slate-400">
                          تومان
                        </span>
                      </p>
                      <AddToCartButton
                        productId={p.id}
                        productTitle={p.title}
                        stock={p.stock}
                      />
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          {/* بقیه محصولات */}
          {rest.length > 0 && (
            <section>
              <h2 className="mb-4 text-base font-bold text-slate-800">
                سایر محصولات پرفروش
              </h2>
              <div className="grid grid-cols-2 items-stretch gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5">
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
