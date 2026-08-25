import Link from "next/link";
import { getProducts } from "@/lib/catalog";
import { discountPercent, formatPrice } from "@/lib/products";
import { fetchSeo, toMetadata } from "@/lib/seo";
import ProductCard from "@/components/product/ProductCard";
import ProductGrid from "@/components/product/ProductGrid";

export const dynamic = "force-dynamic";

export async function generateMetadata() {
  const seo = await fetchSeo("static", "/discounts");
  return toMetadata(seo);
}

export default async function DiscountsPage() {
  // همه‌ی کالاهای تخفیف‌دار — مستقل از انتخاب مدیر برای «شگفت‌انگیزها»
  const { items } = await getProducts({ onlyDiscounted: true, perPage: 50 });

  // بیشترین تخفیف اول؛ محاسبه‌ی درصد از هلپر مشترک می‌آید
  const sorted = [...items].sort(
    (a, b) => discountPercent(b) - discountPercent(a)
  );
  const bestDiscount = sorted.length > 0 ? discountPercent(sorted[0]) : 0;
  const totalSaving = sorted.reduce(
    (sum, product) => sum + ((product.oldPrice ?? product.price) - product.price),
    0
  );

  return (
    <div className="site-shell py-6">
      {/* مسیر راهنما */}
      <nav className="mb-4 flex items-center gap-1 text-xs text-slate-400">
        <Link href="/" className="hover:text-brand-600">
          خانه
        </Link>
        <span>/</span>
        <span className="text-slate-600">تخفیف‌ها</span>
      </nav>

      <section className="mb-6 overflow-hidden rounded-3xl bg-gradient-to-l from-brand-700 to-brand-500">
        <div className="flex flex-col gap-4 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-white/15 text-4xl backdrop-blur">
              🏷️
            </span>
            <div>
              <h1 className="text-xl font-bold text-white">
                همه کالاهای تخفیف‌دار
              </h1>
              <p className="mt-1 text-xs text-white/90 font-num">
                {sorted.length.toLocaleString("fa-IR")} کالا با تخفیف فعال
              </p>
            </div>
          </div>
          <Link
            href="/incredible"
            className="shrink-0 rounded-xl bg-white/15 px-4 py-2.5 text-center text-xs font-bold text-white transition hover:bg-white/25"
          >
            ⚡ پیشنهادهای شگفت‌انگیز
          </Link>
        </div>

        {sorted.length > 0 && (
          <div className="grid grid-cols-2 gap-px border-t border-white/20 bg-white/10">
            <div className="px-4 py-3 text-center">
              <p className="text-sm font-bold text-white font-num">
                ٪{bestDiscount.toLocaleString("fa-IR")}
              </p>
              <p className="text-[11px] text-white/80">بیشترین تخفیف</p>
            </div>
            <div className="px-4 py-3 text-center">
              <p className="text-sm font-bold text-white font-num">
                {formatPrice(totalSaving)}
              </p>
              <p className="text-[11px] text-white/80">مجموع سود شما (تومان)</p>
            </div>
          </div>
        )}
      </section>

      {sorted.length > 0 ? (
        <ProductGrid>
          {sorted.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ProductGrid>
      ) : (
        <div className="rounded-3xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-6xl">🏷️</span>
          <h2 className="mb-2 font-bold text-slate-700">
            در حال حاضر تخفیف فعالی نداریم
          </h2>
          <p className="mb-6 text-sm text-slate-500">
            به‌زودی کالاهای تخفیف‌دار جدید اضافه می‌شود.
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
