import Link from "next/link";
import { notFound } from "next/navigation";
import { getCategories, getProducts } from "@/lib/catalog";
import { breadcrumbSchema, fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import ProductGrid from "@/components/product/ProductGrid";
import JsonLd from "@/components/seo/JsonLd";
import RecentlyViewedSection from "@/components/product/RecentlyViewedSection";

// داده‌ها از دیتابیس (جنگو) خوانده می‌شوند
export const dynamic = "force-dynamic";

// متاتگ‌های سئو از پنل سئو خوانده می‌شوند
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const seo = await fetchSeo("category", slug);
  return toMetadata(seo);
}

const SORTS = [
  { key: "newest", label: "جدیدترین" },
  { key: "popular", label: "پرفروش‌ترین" },
  { key: "cheapest", label: "ارزان‌ترین" },
  { key: "expensive", label: "گران‌ترین" },
] as const;

type Search = {
  sort?: string | string[];
  page?: string | string[];
  search?: string | string[];
  discounted?: string | string[];
};

type CleanSearch = { [Key in keyof Search]?: string };

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

// ساخت آدرس با حفظ بقیه‌ی پارامترها
function buildUrl(slug: string, params: CleanSearch, patch: Partial<CleanSearch>) {
  const merged = { ...params, ...patch };
  const qs = new URLSearchParams();
  if (merged.sort && merged.sort !== "newest") qs.set("sort", merged.sort);
  if (merged.search) qs.set("search", merged.search);
  if (merged.discounted === "1") qs.set("discounted", "1");
  if (merged.page && merged.page !== "1") qs.set("page", merged.page);
  const query = qs.toString();
  return `/category/${slug}${query ? `?${query}` : ""}`;
}

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Search>;
}) {
  const { slug } = await params;
  const sp = await searchParams;
  const current: CleanSearch = {
    sort: single(sp.sort),
    page: single(sp.page),
    search: single(sp.search)?.trim().slice(0, 200),
    discounted: single(sp.discounted),
  };

  const categoriesResult = await Promise.allSettled([getCategories()]);
  if (categoriesResult[0].status === "rejected") {
    return (
      <div className="site-shell py-12">
        <div className="rounded-3xl border border-red-100 bg-red-50 px-6 py-16 text-center">
          <span className="text-5xl" aria-hidden>📡</span>
          <h1 className="mt-4 font-bold text-slate-700">دریافت دسته‌بندی ممکن نشد</h1>
          <p className="mt-2 text-sm text-slate-500">لطفاً چند لحظه دیگر دوباره تلاش کنید.</p>
        </div>
      </div>
    );
  }
  const categories = categoriesResult[0].value;
  const category = categories.find((c) => c.slug === slug);
  if (!category) notFound();

  const sort = (SORTS.some((s) => s.key === current.sort) ? current.sort : "newest") as
    | "newest"
    | "popular"
    | "cheapest"
    | "expensive";
  const rawPage = Number(current.page);
  const page =
    Number.isSafeInteger(rawPage) && rawPage >= 1 && rawPage <= 1_000_000
      ? rawPage
      : 1;
  current.page = String(page);
  const onlyDiscounted = current.discounted === "1";
  const search = current.search || undefined;

  const [productsResult, seoResult] = await Promise.allSettled([
    getProducts({
      categorySlug: slug,
      sort,
      page,
      perPage: 12,
      search,
      onlyDiscounted,
    }),
    fetchSeo("category", slug),
  ]);
  const productsFailed = productsResult.status === "rejected";
  const result =
    productsResult.status === "fulfilled"
      ? productsResult.value
      : { items: [], total: 0, page, perPage: 12, pages: 0 };

  const hasFilter = Boolean(search) || onlyDiscounted;
  const seo = seoResult.status === "fulfilled" ? seoResult.value : null;

  return (
    <div className="site-shell py-6">
      {/* اسکیمای JSON-LD از پنل سئو */}
      {seo?.schema && <JsonLd data={seo.schema} />}
      {seo?.site.breadcrumbsEnabled && (
        <JsonLd
          data={breadcrumbSchema(seo.site, [
            { name: "خانه", path: "/" },
            { name: category.title, path: `/category/${slug}` },
          ])}
        />
      )}
      {/* مسیر راهنما */}
      <nav className="mb-4 flex items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="text-slate-600">{category.title}</span>
      </nav>

      {/* هدر دسته */}
      <section className="mb-6 overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-l from-brand-50 to-white">
        <div className="flex flex-col gap-4 px-6 py-6 sm:flex-row sm:items-center">
          {category.icon && (
            <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-white shadow-sm ring-1 ring-brand-100">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={category.icon}
                alt=""
                className="h-10 w-10 object-contain"
              />
            </span>
          )}
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800">
              {category.title}
            </h1>
            <p className="mt-1 text-xs text-slate-500 font-num">
              {result.total.toLocaleString("fa-IR")} کالا در این دسته‌بندی
            </p>
          </div>
        </div>

        {/* زیردسته‌ها */}
        {category.sub.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t border-brand-100/60 bg-white/60 px-6 py-4">
            {category.sub.map((subcategory) => (
              <Link
                key={subcategory.slug}
                href={`/category/${subcategory.slug}`}
                className="inline-flex min-h-11 items-center rounded-full border border-slate-200 bg-white px-4 py-1.5 text-xs text-slate-600 transition hover:border-brand-400 hover:text-brand-700 sm:min-h-0"
              >
                {subcategory.title}
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* نوار ابزار: مرتب‌سازی و فیلتر */}
      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-100 bg-white px-4 py-3">
        <span className="ml-1 flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <span className="text-base">⇅</span> مرتب‌سازی:
        </span>
        {SORTS.map((s) => (
          <Link
            key={s.key}
            href={buildUrl(slug, current, { sort: s.key, page: "1" })}
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
          href={buildUrl(slug, current, {
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
              href={buildUrl(slug, current, { search: undefined, page: "1" })}
              className="flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1.5 text-brand-700 transition hover:bg-brand-100"
            >
              {search} <span className="text-sm leading-none">×</span>
            </Link>
          )}
          {onlyDiscounted && (
            <Link
              href={buildUrl(slug, current, { discounted: undefined, page: "1" })}
              className="flex items-center gap-1.5 rounded-full bg-accent-50 px-3 py-1.5 text-accent-700 transition hover:bg-accent-100"
            >
              تخفیف‌دار <span className="text-sm leading-none">×</span>
            </Link>
          )}
          <Link
            href={`/category/${slug}`}
            className="text-slate-400 underline-offset-2 hover:text-slate-600 hover:underline"
          >
            حذف همه
          </Link>
        </div>
      )}

      {/* گرید محصولات */}
      {productsFailed ? (
        <div className="rounded-3xl border border-red-100 bg-red-50 px-6 py-16 text-center">
          <span className="mb-4 block text-5xl" aria-hidden>📡</span>
          <h2 className="font-bold text-slate-700">دریافت نتایج جستجو ممکن نشد</h2>
          <p className="mt-2 text-sm text-slate-500">لطفاً چند لحظه دیگر دوباره تلاش کنید.</p>
        </div>
      ) : result.items.length > 0 ? (
        <ProductGrid>
          {result.items.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </ProductGrid>
      ) : (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">🔍</span>
          <h2 className="mb-2 font-bold text-slate-700">
            کالایی با این مشخصات پیدا نشد
          </h2>
          <p className="mb-6 text-sm text-slate-500">
            فیلترها را تغییر دهید یا همه‌ی کالاهای این دسته را ببینید.
          </p>
          <Link
            href={`/category/${slug}`}
            className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مشاهده همه کالاهای {category.title}
          </Link>
        </div>
      )}

      {/* صفحه‌بندی */}
      {result.pages > 1 && (
        <nav className="mt-8 flex flex-wrap items-center justify-center gap-1.5" aria-label="صفحه‌بندی محصولات">
          {page > 1 && (
            <Link
              href={buildUrl(slug, current, { page: String(page - 1) })}
              className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 hover:text-brand-700"
            >
              →
            </Link>
          )}
          {Array.from({ length: result.pages }, (_, i) => i + 1).map((n) => (
            <Link
              key={n}
              href={buildUrl(slug, current, { page: String(n) })}
              className={`grid h-9 w-9 place-items-center rounded-lg border text-sm font-num transition ${
                n === page
                  ? "border-brand-600 bg-brand-600 font-bold text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
              }`}
            >
              {n.toLocaleString("fa-IR")}
            </Link>
          ))}
          {page < result.pages && (
            <Link
              href={buildUrl(slug, current, { page: String(page + 1) })}
              className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 hover:text-brand-700"
            >
              ←
            </Link>
          )}
        </nav>
      )}

      {/* سایر دسته‌ها */}
      <section className="mt-12">
        <h2 className="mb-4 text-base font-bold text-slate-800">
          سایر دسته‌بندی‌ها
        </h2>
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-7">
          {categories
            .filter((c) => c.isTopLevel !== false && c.slug !== slug)
            .map((c) => (
              <Link
                key={c.slug}
                href={`/category/${c.slug}`}
                className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-slate-100 bg-white p-3 transition hover:border-brand-200 hover:shadow-sm"
              >
                {c.icon && (
                  <span className="grid h-11 w-11 place-items-center rounded-full bg-brand-50">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={c.icon}
                      alt=""
                      className="h-7 w-7 object-contain"
                    />
                  </span>
                )}
                <span className="text-center text-[11px] leading-4 text-slate-600">
                  {c.title}
                </span>
              </Link>
            ))}
        </div>
      </section>

      <RecentlyViewedSection className="mt-12" />
    </div>
  );
}
