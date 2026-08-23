import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import ProductCard from "@/components/product/ProductCard";
import { getBrands, getProducts } from "@/lib/catalog";

export const dynamic = "force-dynamic";

const SORTS = [
  { key: "newest", label: "جدیدترین" },
  { key: "popular", label: "پرفروش‌ترین" },
  { key: "cheapest", label: "ارزان‌ترین" },
  { key: "expensive", label: "گران‌ترین" },
] as const;

type Search = {
  sort?: string;
  page?: string;
  discounted?: string;
};

function buildUrl(slug: string, params: Search, patch: Partial<Search>) {
  const merged = { ...params, ...patch };
  const query = new URLSearchParams();
  if (merged.sort && merged.sort !== "newest") query.set("sort", merged.sort);
  if (merged.discounted === "1") query.set("discounted", "1");
  if (merged.page && merged.page !== "1") query.set("page", merged.page);
  const value = query.toString();
  return `/brand/${slug}${value ? `?${value}` : ""}`;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const brand = (await getBrands()).find((item) => item.slug === slug);
  if (!brand) return {};
  return {
    title: `محصولات ${brand.name}`,
    description:
      brand.description ?? `خرید و مشاهده محصولات برند ${brand.name}`,
  };
}

export default async function BrandPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Search>;
}) {
  const { slug } = await params;
  const searchParamsValue = await searchParams;
  const brands = await getBrands();
  const brand = brands.find((item) => item.slug === slug);
  if (!brand) notFound();

  const sort = (
    SORTS.some((item) => item.key === searchParamsValue.sort)
      ? searchParamsValue.sort
      : "newest"
  ) as "newest" | "popular" | "cheapest" | "expensive";
  const page = Math.max(1, Number(searchParamsValue.page) || 1);
  const onlyDiscounted = searchParamsValue.discounted === "1";
  const result = await getProducts({
    brandSlug: slug,
    sort,
    page,
    perPage: 12,
    onlyDiscounted,
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <nav className="mb-4 flex items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="text-slate-600">{brand.name}</span>
      </nav>

      <section className="mb-6 rounded-3xl border border-brand-100 bg-gradient-to-l from-brand-50 to-white px-6 py-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          {brand.logo && (
            <span className="grid h-20 w-20 shrink-0 place-items-center rounded-2xl bg-white shadow-sm ring-1 ring-brand-100">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={brand.logo}
                alt={`نشان ${brand.name}`}
                className="h-14 w-14 object-contain"
              />
            </span>
          )}
          <div className="min-w-0 flex-1">
            <h1 className="text-xl font-bold text-slate-800">
              محصولات {brand.name}
            </h1>
            {brand.description && (
              <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-500">
                {brand.description}
              </p>
            )}
            <p className="mt-2 text-xs text-slate-500 font-num">
              {result.total.toLocaleString("fa-IR")} کالا از این برند
            </p>
          </div>
          {brand.website && (
            <a
              href={brand.website}
              target="_blank"
              rel="noreferrer"
              className="self-start rounded-xl border border-brand-200 bg-white px-4 py-2 text-xs font-medium text-brand-700 transition hover:bg-brand-50"
            >
              وب‌سایت رسمی ↗
            </a>
          )}
        </div>
      </section>

      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-100 bg-white px-4 py-3">
        <span className="ml-1 text-xs font-medium text-slate-500">
          ⇅ مرتب‌سازی:
        </span>
        {SORTS.map((item) => (
          <Link
            key={item.key}
            href={buildUrl(slug, searchParamsValue, {
              sort: item.key,
              page: "1",
            })}
            className={`rounded-lg px-3 py-1.5 text-xs transition ${
              sort === item.key
                ? "bg-brand-50 font-bold text-brand-700"
                : "text-slate-500 hover:text-brand-700"
            }`}
          >
            {item.label}
          </Link>
        ))}
        <Link
          href={buildUrl(slug, searchParamsValue, {
            discounted: onlyDiscounted ? undefined : "1",
            page: "1",
          })}
          className={`mr-auto rounded-lg px-3 py-1.5 text-xs transition ${
            onlyDiscounted
              ? "bg-accent-50 font-bold text-accent-700"
              : "text-slate-500 hover:text-accent-700"
          }`}
        >
          فقط تخفیف‌دارها
        </Link>
      </div>

      {result.items.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {result.items.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      ) : (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">🔍</span>
          <h2 className="mb-2 font-bold text-slate-700">
            محصولی از این برند پیدا نشد
          </h2>
          {onlyDiscounted && (
            <Link
              href={`/brand/${slug}`}
              className="mt-4 inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white"
            >
              مشاهده همه محصولات {brand.name}
            </Link>
          )}
        </div>
      )}

      {result.pages > 1 && (
        <nav className="mt-8 flex flex-wrap items-center justify-center gap-1.5" aria-label="صفحه‌بندی محصولات برند">
          {Array.from({ length: result.pages }, (_, index) => index + 1).map(
            (number) => (
              <Link
                key={number}
                href={buildUrl(slug, searchParamsValue, {
                  page: String(number),
                })}
                className={`grid h-9 w-9 place-items-center rounded-lg border text-sm font-num transition ${
                  number === page
                    ? "border-brand-600 bg-brand-600 font-bold text-white"
                    : "border-slate-200 bg-white text-slate-600 hover:border-brand-400"
                }`}
              >
                {number.toLocaleString("fa-IR")}
              </Link>
            )
          )}
        </nav>
      )}

      {brands.length > 1 && (
        <section className="mt-12">
          <h2 className="mb-4 text-base font-bold text-slate-800">
            سایر برندها
          </h2>
          <div className="flex flex-wrap gap-2">
            {brands
              .filter((item) => item.slug !== slug)
              .map((item) => (
                <Link
                  key={item.slug}
                  href={`/brand/${item.slug}`}
                  className="rounded-xl border border-slate-100 bg-white px-4 py-2 text-xs text-slate-600 transition hover:border-brand-200 hover:text-brand-700"
                >
                  {item.name}
                </Link>
              ))}
          </div>
        </section>
      )}
    </div>
  );
}
