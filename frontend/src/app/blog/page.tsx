import type { Metadata } from "next";
import Link from "next/link";
import BlogCard from "@/components/blog/BlogCard";
import { getBlogPosts, getBlogTaxonomies, SITE_URL } from "@/lib/blog";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "وبلاگ کشاورزی | گروه صنعتی توانا",
  description:
    "آموزش‌ها، راهنماهای خرید و تازه‌ترین مطالب کاربردی درباره ابزارآلات، باغبانی و کشاورزی.",
  alternates: { canonical: `${SITE_URL}/blog` },
  openGraph: {
    title: "وبلاگ کشاورزی گروه صنعتی توانا",
    description: "راهنماهای کاربردی ابزارآلات، باغبانی و کشاورزی",
    type: "website",
    locale: "fa_IR",
    url: `${SITE_URL}/blog`,
  },
};

type Search = {
  category?: string | string[];
  tag?: string | string[];
  search?: string | string[];
  page?: string | string[];
};

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function blogUrl(
  current: { category?: string; tag?: string; search?: string; page?: number },
  patch: Partial<{ category?: string; tag?: string; search?: string; page?: number }>
) {
  const values = { ...current, ...patch };
  const query = new URLSearchParams();
  if (values.category) query.set("category", values.category);
  if (values.tag) query.set("tag", values.tag);
  if (values.search) query.set("search", values.search);
  if (values.page && values.page > 1) query.set("page", String(values.page));
  return `/blog${query.size ? `?${query}` : ""}`;
}

export default async function BlogPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const raw = await searchParams;
  const current = {
    category: single(raw.category)?.trim() || undefined,
    tag: single(raw.tag)?.trim() || undefined,
    search: single(raw.search)?.trim() || undefined,
    page: Math.max(1, Number(single(raw.page)) || 1),
  };

  const [postsResult, taxonomyResult] = await Promise.allSettled([
    getBlogPosts({ ...current, perPage: 9 }),
    getBlogTaxonomies(),
  ]);
  const result = postsResult.status === "fulfilled" ? postsResult.value : null;
  const taxonomies =
    taxonomyResult.status === "fulfilled"
      ? taxonomyResult.value
      : { categories: [], tags: [] };
  const activeCategory = taxonomies.categories.find(
    (item) => item.slug === current.category
  );
  const activeTag = taxonomies.tags.find((item) => item.slug === current.tag);

  return (
    <div className="site-shell py-8">
      <nav className="mb-5 flex items-center gap-1 text-xs text-slate-400" aria-label="مسیر صفحه">
        <Link href="/" className="hover:text-brand-600">خانه</Link>
        <span>/</span>
        <span className="text-slate-600">وبلاگ</span>
      </nav>

      <header className="mb-7 overflow-hidden rounded-3xl bg-gradient-to-l from-brand-700 via-brand-600 to-emerald-500 px-6 py-9 text-white sm:px-10">
        <span className="text-4xl" aria-hidden>🌿</span>
        <h1 className="mt-3 text-2xl font-bold sm:text-3xl">وبلاگ کشاورزی توانا</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-emerald-50">
          راهنماهای ساده و کاربردی برای انتخاب ابزار، نگهداری تجهیزات و تجربه بهتر در باغبانی و کشاورزی.
        </p>
      </header>

      <div className="mb-6 rounded-2xl border border-slate-100 bg-white p-4">
        <form action="/blog" className="flex flex-col gap-3 sm:flex-row" role="search">
          {current.category && <input type="hidden" name="category" value={current.category} />}
          {current.tag && <input type="hidden" name="tag" value={current.tag} />}
          <label className="sr-only" htmlFor="blog-search">جستجو در وبلاگ</label>
          <input
            id="blog-search"
            name="search"
            defaultValue={current.search}
            placeholder="جستجو در عنوان و متن نوشته‌ها..."
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white"
          />
          <button className="rounded-xl bg-brand-600 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-brand-700">
            جستجو
          </button>
        </form>

        {taxonomies.categories.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 text-xs">
            <span className="text-slate-400">دسته‌ها:</span>
            {taxonomies.categories.map((category) => (
              <Link
                key={category.id}
                href={blogUrl(current, {
                  category: current.category === category.slug ? undefined : category.slug,
                  page: 1,
                })}
                className={`rounded-full px-3 py-1.5 transition ${
                  current.category === category.slug
                    ? "bg-brand-600 font-medium text-white"
                    : "bg-brand-50 text-brand-700 hover:bg-brand-100"
                }`}
              >
                {category.name} ({(category.postsCount ?? 0).toLocaleString("fa-IR")})
              </Link>
            ))}
          </div>
        )}

        {taxonomies.tags.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-400">برچسب‌ها:</span>
            {taxonomies.tags.map((tag) => (
              <Link
                key={tag.id}
                href={blogUrl(current, {
                  tag: current.tag === tag.slug ? undefined : tag.slug,
                  page: 1,
                })}
                className={`rounded-lg border px-2.5 py-1 transition ${
                  current.tag === tag.slug
                    ? "border-slate-700 bg-slate-700 text-white"
                    : "border-slate-200 text-slate-500 hover:border-brand-300 hover:text-brand-700"
                }`}
              >
                #{tag.name}
              </Link>
            ))}
          </div>
        )}
      </div>

      {(activeCategory || activeTag || current.search) && (
        <div className="mb-5 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400">فیلتر فعال:</span>
          {activeCategory && <span className="rounded-full bg-brand-50 px-3 py-1.5 text-brand-700">{activeCategory.name}</span>}
          {activeTag && <span className="rounded-full bg-slate-100 px-3 py-1.5 text-slate-600">#{activeTag.name}</span>}
          {current.search && <span className="rounded-full bg-amber-50 px-3 py-1.5 text-amber-700">«{current.search}»</span>}
          <Link href="/blog" className="text-red-400 hover:underline">حذف فیلترها</Link>
        </div>
      )}

      {!result ? (
        <section className="rounded-3xl border border-red-100 bg-red-50 px-6 py-14 text-center">
          <span className="text-5xl" aria-hidden>📡</span>
          <h2 className="mt-4 font-bold text-slate-700">دریافت نوشته‌ها ممکن نشد</h2>
          <p className="mt-2 text-sm text-slate-500">لطفاً چند لحظه دیگر صفحه را تازه‌سازی کنید.</p>
        </section>
      ) : result.items.length === 0 ? (
        <section className="rounded-3xl border border-slate-100 bg-white px-6 py-14 text-center">
          <span className="text-5xl" aria-hidden>🔎</span>
          <h2 className="mt-4 font-bold text-slate-700">نوشته‌ای پیدا نشد</h2>
          <p className="mt-2 text-sm text-slate-500">عبارت جستجو یا فیلترها را تغییر دهید.</p>
          <Link href="/blog" className="mt-5 inline-block rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white">مشاهده همه نوشته‌ها</Link>
        </section>
      ) : (
        <>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-800">تازه‌ترین نوشته‌ها</h2>
            <span className="text-xs text-slate-400">{result.total.toLocaleString("fa-IR")} مطلب</span>
          </div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {result.items.map((post) => <BlogCard key={post.id} post={post} />)}
          </div>
          {result.pages > 1 && (
            <nav className="mt-8 flex flex-wrap justify-center gap-1.5" aria-label="صفحه‌بندی وبلاگ">
              {Array.from({ length: result.pages }, (_, index) => index + 1).map((page) => (
                <Link
                  key={page}
                  href={blogUrl(current, { page })}
                  aria-current={page === result.page ? "page" : undefined}
                  className={`grid h-9 w-9 place-items-center rounded-lg border text-sm transition ${
                    page === result.page
                      ? "border-brand-600 bg-brand-600 font-bold text-white"
                      : "border-slate-200 bg-white text-slate-600 hover:border-brand-400"
                  }`}
                >
                  {page.toLocaleString("fa-IR")}
                </Link>
              ))}
            </nav>
          )}
        </>
      )}
    </div>
  );
}
