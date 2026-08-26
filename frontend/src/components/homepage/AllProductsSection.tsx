"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import ProductCard from "@/components/product/ProductCard";
import ProductGrid from "@/components/product/ProductGrid";
import { api } from "@/lib/client-api";
import {
  ALL_PRODUCTS_PATH,
  HOME_PRODUCTS_PER_PAGE,
  type Product,
} from "@/lib/products";

export type ProductPage = {
  items: Product[];
  total: number;
  pages: number;
};

/** پنجره‌ی شماره‌ی صفحه‌ها حول صفحه‌ی جاری — فهرست کامل صفحات طولانی می‌شود */
function pageWindow(page: number, pages: number, size = 5): number[] {
  const start = Math.max(
    1,
    Math.min(page - Math.floor(size / 2), pages - size + 1)
  );
  const end = Math.min(pages, start + size - 1);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

/**
 * بخش «همه محصولات» صفحه اصلی — به‌صورت پیش‌فرض شش کالا در هر صفحه.
 *
 * جای این بخش، عنوان و تعداد هر صفحه‌اش از پنل مدیریت صفحه اصلی می‌آید.
 * صفحه‌ی اول سمت سرور رندر می‌شود (بدون پرش و قابل ایندکس) و صفحه‌های بعدی
 * از همان API عمومی محصولات گرفته می‌شوند تا کل صفحه دوباره بار نشود.
 */
export default function AllProductsSection({
  title = "همه محصولات",
  perPage = HOME_PRODUCTS_PER_PAGE,
  initial,
}: {
  title?: string;
  perPage?: number;
  initial: ProductPage;
}) {
  const [page, setPage] = useState(1);
  const [current, setCurrent] = useState<ProductPage>(initial);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // آخرین صفحه‌ای که واقعاً نمایش داده شده — برای برگشت در صورت خطا
  const shownPage = useRef(1);
  const requestId = useRef(0);
  const gridRef = useRef<HTMLDivElement>(null);

  // درخواست‌های در راه پس از خروج از صفحه نباید state را دست بزنند
  useEffect(() => {
    return () => {
      requestId.current += 1;
    };
  }, []);

  const load = useCallback(
    async (target: number) => {
      const thisRequest = ++requestId.current;
      setLoading(true);
      setError(null);

      const result = await api.get<ProductPage>(
        `/api/products?page=${target}&perPage=${perPage}&sort=newest`
      );
      if (requestId.current !== thisRequest) return;

      setLoading(false);
      if (!result.ok || !result.data) {
        setError(result.error ?? "دریافت محصولات با خطا روبه‌رو شد");
        setPage(shownPage.current);
        return;
      }

      const { items, total, pages } = result.data;
      setCurrent({ items, total, pages });
      shownPage.current = target;
    },
    [perPage]
  );

  function goTo(target: number) {
    if (loading || target === page || target < 1 || target > current.pages) {
      return;
    }
    setPage(target);
    void load(target);
    gridRef.current?.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  // فروشگاه بدون محصول، بخش خالی نشان نمی‌دهد
  if (initial.total === 0) return null;

  const numbers = pageWindow(page, current.pages);
  const arrowClass =
    "grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:border-brand-400 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-200 disabled:hover:text-slate-500";

  return (
    <section aria-labelledby="all-products-heading">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2
          id="all-products-heading"
          className="text-lg font-bold text-slate-800"
        >
          🛒 {title}
          <span className="mr-2 text-xs font-normal text-slate-400 font-num">
            ({current.total.toLocaleString("fa-IR")} کالا)
          </span>
        </h2>
        <Link
          href={ALL_PRODUCTS_PATH}
          className="shrink-0 rounded-xl bg-brand-50 px-4 py-2 text-xs font-medium text-brand-700 transition hover:bg-brand-100"
        >
          مشاهده همه محصولات ←
        </Link>
      </div>

      <div
        ref={gridRef}
        aria-busy={loading}
        className={`transition-opacity ${loading ? "opacity-60" : ""}`}
      >
        <ProductGrid>
          {current.items.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ProductGrid>
      </div>

      {error && (
        <p role="alert" className="mt-3 text-center text-xs text-rose-600">
          {error}
        </p>
      )}

      {current.pages > 1 && (
        <nav
          aria-label="صفحه‌بندی همه محصولات"
          className="mt-5 flex flex-wrap items-center justify-center gap-1.5"
        >
          <button
            type="button"
            onClick={() => goTo(page - 1)}
            disabled={page === 1 || loading}
            aria-label="صفحه قبل"
            className={arrowClass}
          >
            →
          </button>
          {numbers[0] > 1 && <span className="px-1 text-slate-300">…</span>}
          {numbers.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => goTo(n)}
              disabled={loading && n !== page}
              aria-current={n === page ? "page" : undefined}
              className={`grid h-9 w-9 place-items-center rounded-lg border text-sm font-num transition ${
                n === page
                  ? "border-brand-600 bg-brand-600 font-bold text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-brand-400 hover:text-brand-700"
              }`}
            >
              {n.toLocaleString("fa-IR")}
            </button>
          ))}
          {numbers[numbers.length - 1] < current.pages && (
            <span className="px-1 text-slate-300">…</span>
          )}
          <button
            type="button"
            onClick={() => goTo(page + 1)}
            disabled={page === current.pages || loading}
            aria-label="صفحه بعد"
            className={arrowClass}
          >
            ←
          </button>
        </nav>
      )}

      <div className="mt-5 text-center">
        <Link
          href={ALL_PRODUCTS_PATH}
          className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          مشاهده بیشتر
        </Link>
      </div>
    </section>
  );
}
