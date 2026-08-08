import Link from "next/link";
import { getProducts } from "@/lib/catalog";
import { formatPrice } from "@/lib/products";
import { fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import DealCountdown from "@/components/product/DealCountdown";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const seo = await fetchSeo("static", "/incredible");
  return toMetadata(seo);
}

export default async function IncrediblePage() {
  // فقط کالاهای تخفیف‌دار، بیشترین تخفیف اول
  const { items } = await getProducts({
    onlyDiscounted: true,
    perPage: 50,
  });

  const sorted = [...items].sort((a, b) => {
    const da = a.oldPrice ? 1 - a.price / a.oldPrice : 0;
    const db = b.oldPrice ? 1 - b.price / b.oldPrice : 0;
    return db - da;
  });

  const best = sorted[0];
  const bestDiscount = best?.oldPrice
    ? Math.round((1 - best.price / best.oldPrice) * 100)
    : 0;
  const totalSaving = sorted.reduce(
    (sum, p) => sum + ((p.oldPrice ?? p.price) - p.price),
    0
  );

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* مسیر راهنما */}
      <nav className="mb-4 flex items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="text-slate-600">شگفت‌انگیزها</span>
      </nav>

      {/* هدر پیشنهادهای ویژه با تایمر */}
      <section className="mb-6 overflow-hidden rounded-3xl bg-gradient-to-l from-accent-600 to-accent-400">
        <div className="flex flex-col gap-4 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-secondary-900/10 text-4xl backdrop-blur">
              ⚡
            </span>
            <div>
              <h1 className="text-xl font-bold text-secondary-900">
                پیشنهاد شگفت‌انگیز
              </h1>
              <p className="mt-1 text-xs text-secondary-900/90 font-num">
                {sorted.length.toLocaleString("fa-IR")} کالا با تخفیف ویژه
              </p>
            </div>
          </div>
          <DealCountdown />
        </div>

        {/* نوار آمار */}
        {sorted.length > 0 && (
          <div className="grid grid-cols-2 gap-px border-t border-secondary-900/20 bg-secondary-900/5 sm:grid-cols-3">
            <div className="bg-transparent px-4 py-3 text-center">
              <p className="text-sm font-bold text-secondary-900 font-num">
                ٪{bestDiscount.toLocaleString("fa-IR")}
              </p>
              <p className="text-[11px] text-secondary-900/80">بیشترین تخفیف</p>
            </div>
            <div className="bg-transparent px-4 py-3 text-center">
              <p className="text-sm font-bold text-secondary-900 font-num">
                {formatPrice(totalSaving)}
              </p>
              <p className="text-[11px] text-secondary-900/80">مجموع سود شما (تومان)</p>
            </div>
            <div className="col-span-2 bg-transparent px-4 py-3 text-center sm:col-span-1">
              <p className="text-sm font-bold text-secondary-900">🚚 ارسال سریع</p>
              <p className="text-[11px] text-secondary-900/80">به سراسر کشور</p>
            </div>
          </div>
        )}
      </section>

      {/* پیشنهاد ویژه‌ی امروز */}
      {best && (
        <section className="mb-6 overflow-hidden rounded-3xl border-2 border-accent-100 bg-white">
          <div className="flex items-center gap-2 bg-accent-50 px-5 py-2.5">
            <span className="text-sm">🔥</span>
            <h2 className="text-xs font-bold text-accent-800">
              داغ‌ترین پیشنهاد امروز
            </h2>
          </div>
          <Link
            href={`/product/${best.id}`}
            className="group flex flex-col gap-5 p-5 sm:flex-row sm:items-center"
          >
            {best.image && (
              <div className="h-40 w-full shrink-0 overflow-hidden rounded-2xl bg-slate-50 sm:w-40">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={best.image}
                  alt={best.title}
                  className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                />
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h3 className="mb-2 text-base font-bold leading-7 text-slate-800 group-hover:text-accent-700">
                {best.title}
              </h3>
              <p className="mb-4 text-xs text-slate-400">{best.category}</p>
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-lg bg-accent-500 px-2.5 py-1 text-sm font-bold text-secondary-900 font-num">
                  ٪{bestDiscount.toLocaleString("fa-IR")}
                </span>
                <span className="text-sm text-slate-300 line-through font-num">
                  {formatPrice(best.oldPrice!)}
                </span>
                <span className="text-xl font-bold text-slate-800 font-num">
                  {formatPrice(best.price)}
                  <span className="mr-1 text-xs font-normal text-slate-400">
                    تومان
                  </span>
                </span>
              </div>
            </div>
            <span className="shrink-0 rounded-xl bg-accent-500 px-6 py-3 text-center text-sm font-bold text-secondary-900 transition group-hover:bg-accent-600">
              مشاهده و خرید
            </span>
          </Link>
        </section>
      )}

      {/* گرید محصولات تخفیف‌دار */}
      {sorted.length > 0 ? (
        <>
          <h2 className="mb-4 text-base font-bold text-slate-800">
            همه‌ی کالاهای تخفیف‌دار
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {sorted.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">🏷️</span>
          <h2 className="mb-2 font-bold text-slate-700">
            در حال حاضر تخفیف فعالی نداریم
          </h2>
          <p className="mb-6 text-sm text-slate-500">
            به‌زودی پیشنهادهای شگفت‌انگیز جدید اضافه می‌شود.
          </p>
          <Link
            href="/"
            className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مشاهده همه محصولات
          </Link>
        </div>
      )}
    </div>
  );
}
