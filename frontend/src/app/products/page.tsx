import Link from "next/link";
import { getCategories, getProducts } from "@/lib/catalog";
import { breadcrumbSchema, fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import ProductGrid from "@/components/product/ProductGrid";
import JsonLd from "@/components/seo/JsonLd";

// داده‌ها از دیتابیس (جنگو) خوانده می‌شوند
export const dynamic = "force-dynamic";

// متاتگ‌های سئو از پنل سئو خوانده می‌شوند
export async function generateMetadata() {
  const seo = await fetchSeo("static", "/products");
  return toMetadata(seo);
}

const SORTS = [
  { key: "newest", label: "جدیدترین" },
  { key: "popular", label: "پرفروش‌ترین" },
  { key: "cheapest", label: "ارزان‌ترین" },
  { key: "expensive", label: "گران‌ترین" },
] as const;

type SortKey = (typeof SORTS)[number]["key"];

const PER_PAGE = 24;

type Search = {
  sort?: string;
  page?: string;
  search?: string;
  category?: string;
  discounted?: string;
};

// ساخت آدرس با حفظ بقیه‌ی پارامترها
function buildUrl(params: Search, patch: Partial<Search>) {
  const merged: Search = { ...params, ...patch };
  const qs = new URLSearchParams();
  if (merged.sort && merged.sort !== "newest") qs.set("sort", merged.sort);
  if (merged.search) qs.set("search", merged.search);
  if (merged.category) qs.set("category", merged.category);
  if (merged.discounted === "1") qs.set("discounted", "1");
  if (merged.page && merged.page !== "1") qs.set("page", merged.page);
  const query = qs.toString();
  return `/products${query ? `?${query}` : ""}`;
}

/** پنجره‌ی شماره‌ی صفحه‌ها حول صفحه‌ی جاری — کاتالوگ کامل صفحات زیادی دارد */
function pageWindow(page: number, pages: number, size = 7): number[] {
  const start = Math.max(
    1,
    Math.min(page - Math.floor(size / 2), pages - size + 1)
  );
  const end = Math.min(pages, start + size - 1);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

export default async function AllProductsPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const sp = await searchParams;

  const sort = (
    SORTS.some((s) => s.key === sp.sort) ? sp.sort : "newest"
  ) as SortKey;
  const page = Math.max(1, Number(sp.page) || 1);
  const onlyDiscounted = sp.discounted === "1";
  const search = sp.search?.trim() || undefined;

  const [categories, result, seo] = await Promise.all([
    getCategories(),
    getProducts({
      sort,
      page,
      perPage: PER_PAGE,
      search,
      categorySlug: sp.category,
      onlyDiscounted,
    }),
    fetchSeo("static", "/products"),
  ]);

  const rootCategories = categories.filter(
    (category) => category.isTopLevel !== false
  );
  const activeCategory = categories.find((c) => c.slug === sp.category);
  const hasFilter = Boolean(search) || onlyDiscounted || Boolean(sp.category);
  const numbers = pageWindow(page, result.pages);

  return (
    <div className="site-shell py-6">
      {/* اسکیمای JSON-LD از پنل سئو */}
      {seo?.schema && <JsonLd data={seo.schema} />}
      {seo?.site.breadcrumbsEnabled && (
        <JsonLd
          data={breadcrumbSchema(seo.site, [
            { name: "خانه", path: "/" },
            { name: "همه محصولات", path: "/products" },
          ])}
        />
      )}

      {/* مسیر راهنما */}
      <nav className="mb-4 flex items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="text-slate-600">همه محصولات</span>
      </nav>

      {/* هدر */}
      <section className="mb-6 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-l from-brand-50 to-white px-6 py-6">
        <div className="flex items-center gap-4">
          <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-white text-4xl shadow-sm ring-1 ring-brand-100">
            🛒
          </span>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800">
              همه محصولات
              {activeCategory && (
                <span className="text-base font-normal">
                  {" "}
                  — {activeCategory.title}
                </span>
              )}
            </h1>
            <p className="mt-1 text-xs text-slate-500 font-num">
              {result.total.toLocaleString("fa-IR")} کالا در فروشگاه
            </p>
          </div>
        </div>
      </section>

      {/* فیلتر دسته‌بندی */}
      <div className="mb-4 flex flex-wrap gap-2">
        <Link
          href={buildUrl(sp, { category: undefined, page: "1" })}
          className={`inline-flex min-h-11 items-center rounded-full border px-4 py-1.5 text-xs transition sm:min-h-0 ${
            !sp.category
              ? "border-brand-500 bg-brand-600 font-medium text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
          }`}
        >
          همه دسته‌ها
        </Link>
        {rootCategories.map((category) => (
          <Link
            key={category.slug}
            href={buildUrl(sp, { category: category.slug, page: "1" })}
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-full border px-4 py-1.5 text-xs transition sm:min-h-0 ${
              sp.category === category.slug
                ? "border-brand-500 bg-brand-600 font-medium text-white"
                : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
            }`}
          >
            {category.icon && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={category.icon}
                alt=""
                className="h-4 w-4 shrink-0 object-contain"
              />
            )}
            {category.title}
          </Link>
        ))}
      </div>

      {/* نوار ابزار: مرتب‌سازی و فیلتر */}
      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-100 bg-white px-4 py-3">
        <span className="ml-1 flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <span className="text-base">⇅</span> مرتب‌سازی:
        </span>
        {SORTS.map((s) => (
          <Link
            key={s.key}
            href={buildUrl(sp, { sort: s.key, page: "1" })}
            className={`rounded-lg px-3 py-1.5 text-xs transition ${
              sort === s.key
                ? "bg-brand-50 font-bold text-brand-700"
                : "text-slate-500 hover:text-brand-700"
            }`}
          >
            {s.label}
          </Link>
        ))}

        <span className="mx-2 hidden h-5 w-px bg-slate-200 sm:block" />

        <Link
          href={buildUrl(sp, {
            discounted: onlyDiscounted ? undefined : "1",
            page: "1",
          })}
          className={`mr-auto flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs transition sm:mr-0 ${
            onlyDiscounted
              ? "bg-accent-50 font-bold text-accent-700"
              : "text-slate-500 hover:text-accent-700"
          }`}
        >
          <span
            className={`relative h-4 w-7 rounded-full transition ${
              onlyDiscounted ? "bg-accent-500" : "bg-slate-300"
            }`}
          >
            <span
              className={`absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all ${
                onlyDiscounted ? "right-0.5" : "right-3.5"
              }`}
            />
          </span>
          فقط تخفیف‌دارها
        </Link>
      </div>

      {/* فیلتر فعال */}
      {hasFilter && (
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400">فیلترهای فعال:</span>
          {search && (
            <Link
              href={buildUrl(sp, { search: undefined, page: "1" })}
              className="flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1.5 text-brand-700 transition hover:bg-brand-100"
            >
              {search} <span className="text-sm leading-none">×</span>
            </Link>
          )}
          {activeCategory && (
            <Link
              href={buildUrl(sp, { category: undefined, page: "1" })}
              className="flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1.5 text-brand-700 transition hover:bg-brand-100"
            >
              {activeCategory.title} <span className="text-sm leading-none">×</span>
            </Link>
          )}
          {onlyDiscounted && (
            <Link
              href={buildUrl(sp, { discounted: undefined, page: "1" })}
              className="flex items-center gap-1.5 rounded-full bg-accent-50 px-3 py-1.5 text-accent-700 transition hover:bg-accent-100"
            >
              تخفیف‌دار <span className="text-sm leading-none">×</span>
            </Link>
          )}
          <Link
            href="/products"
            className="text-slate-400 underline-offset-2 hover:text-slate-600 hover:underline"
          >
            حذف همه
          </Link>
        </div>
      )}

      {/* گرید محصولات */}
      {result.items.length > 0 ? (
        <ProductGrid>
          {result.items.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ProductGrid>
      ) : (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">🔍</span>
          <h2 className="mb-2 font-bold text-slate-700">
            {hasFilter
              ? "کالایی با این مشخصات پیدا نشد"
              : "هنوز محصولی ثبت نشده است"}
          </h2>
          {hasFilter && (
            <>
              <p className="mb-6 text-sm text-slate-500">
                فیلترها را تغییر دهید یا همه‌ی کالاهای فروشگاه را ببینید.
              </p>
              <Link
                href="/products"
                className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
              >
                مشاهده همه محصولات
              </Link>
            </>
          )}
        </div>
      )}

      {/* صفحه‌بندی */}
      {result.pages > 1 && (
        <nav
          className="mt-8 flex flex-wrap items-center justify-center gap-1.5"
          aria-label="صفحه‌بندی محصولات"
        >
          {page > 1 && (
            <Link
              href={buildUrl(sp, { page: String(page - 1) })}
              aria-label="صفحه قبل"
              className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 hover:text-brand-700"
            >
              →
            </Link>
          )}
          {numbers[0] > 1 && <span className="px-1 text-slate-300">…</span>}
          {numbers.map((n) => (
            <Link
              key={n}
              href={buildUrl(sp, { page: String(n) })}
              aria-current={n === page ? "page" : undefined}
              className={`grid h-9 w-9 place-items-center rounded-lg border text-sm font-num transition ${
                n === page
                  ? "border-brand-600 bg-brand-600 font-bold text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
              }`}
            >
              {n.toLocaleString("fa-IR")}
            </Link>
          ))}
          {numbers[numbers.length - 1] < result.pages && (
            <span className="px-1 text-slate-300">…</span>
          )}
          {page < result.pages && (
            <Link
              href={buildUrl(sp, { page: String(page + 1) })}
              aria-label="صفحه بعد"
              className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 hover:text-brand-700"
            >
              ←
            </Link>
          )}
        </nav>
      )}
    </div>
  );
}
