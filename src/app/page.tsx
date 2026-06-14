import Link from "next/link";
import { categories, products } from "@/lib/products";
import ProductCard from "@/components/product/ProductCard";

export default function Home() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* بنر اصلی */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-l from-brand-700 to-brand-500 px-6 py-12 text-white sm:px-12 sm:py-16">
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
          {categories.map((c) => (
            <Link
              key={c.slug}
              href={`/category/${c.slug}`}
              className="flex flex-col items-center gap-2 rounded-2xl border border-slate-100 bg-white p-4 transition hover:border-brand-200 hover:shadow-sm"
            >
              <span className="grid h-14 w-14 place-items-center rounded-full bg-brand-50 text-2xl">
                {c.emoji}
              </span>
              <span className="text-center text-xs text-slate-600">
                {c.title}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* محصولات */}
      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-800">🔥 پرفروش‌ترین‌ها</h2>
          <Link
            href="/category/garden-tools"
            className="text-sm text-brand-600 transition hover:text-brand-700"
          >
            مشاهده همه ←
          </Link>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </section>
    </div>
  );
}
