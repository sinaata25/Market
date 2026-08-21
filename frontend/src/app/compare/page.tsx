"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { formatPrice, type Product, type ProductSpecification } from "@/lib/products";
import { api } from "@/lib/client-api";
import { MAX_COMPARE_ITEMS, MIN_COMPARE_ITEMS, useCompare } from "@/lib/compare";

type CompareProduct = Product & { specifications: ProductSpecification[] };

// ردیف مشخصات: اتحاد کلیدهای مشخصه‌ی همه‌ی محصولات انتخاب‌شده
function specificationRows(items: CompareProduct[]) {
  const order: string[] = [];
  const names: Record<string, string> = {};
  for (const item of items) {
    for (const spec of item.specifications) {
      if (!(spec.slug in names)) {
        order.push(spec.slug);
        names[spec.slug] = spec.name;
      }
    }
  }
  return order.map((slug) => ({
    slug,
    name: names[slug],
    values: items.map(
      (item) => item.specifications.find((s) => s.slug === slug)?.value ?? null
    ),
  }));
}

type CompareResult = {
  key: string;
  products: CompareProduct[] | null;
  error: string;
};

const EMPTY_RESULT: CompareResult = { key: "", products: null, error: "" };

export default function ComparePage() {
  const { items: trayItems, count, remove, clear } = useCompare();
  const [result, setResult] = useState<CompareResult>(EMPTY_RESULT);
  const requestRef = useRef(0);

  const ids = trayItems.map((item) => item.id);
  const idsKey = ids.join(",");

  // درخواست فقط داخل callback غیرهمزمان state را تغییر می‌دهد؛ لودینگ/خطا از مقایسه‌ی
  // idsKey جاری با کلید نتیجه‌ی آخرین درخواست به‌دست می‌آید (بدون setState همزمان در افکت)
  useEffect(() => {
    if (ids.length < MIN_COMPARE_ITEMS) return;
    const requestId = ++requestRef.current;
    api
      .post<{ items: CompareProduct[] }>("/api/products/compare", {
        productIds: ids,
      })
      .then((res) => {
        if (requestId !== requestRef.current) return;
        setResult(
          res.ok && res.data
            ? { key: idsKey, products: res.data.items, error: "" }
            : {
                key: idsKey,
                products: null,
                error: res.error ?? "مقایسه‌ی این محصولات امکان‌پذیر نیست",
              }
        );
      });
    // idsKey برای جلوگیری از فراخوانی مجدد به‌ازای تغییر مرجع آرایه استفاده می‌شود
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsKey]);

  const resolved = result.key === idsKey;
  const products = resolved ? result.products : null;
  const error = resolved ? result.error : "";
  const loading = ids.length >= MIN_COMPARE_ITEMS && !resolved;

  if (count < MIN_COMPARE_ITEMS) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <span className="mb-4 block text-5xl">⇄</span>
        <h1 className="mb-2 text-lg font-bold text-slate-800">
          محصولی برای مقایسه انتخاب نشده است
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          برای مقایسه، حداقل {MIN_COMPARE_ITEMS.toLocaleString("fa-IR")} محصول
          از یک دسته‌بندی مشترک را از فروشگاه انتخاب کنید.
          {count === 1 && " یک محصول انتخاب کرده‌اید."}
        </p>
        <Link
          href="/"
          className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          مشاهده محصولات
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 text-center text-sm text-slate-400">
        در حال بارگذاری مقایسه...
      </div>
    );
  }

  if (error || !products) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <span className="mb-4 block text-5xl">⚠️</span>
        <h1 className="mb-2 text-lg font-bold text-slate-800">
          مقایسه ممکن نیست
        </h1>
        <p className="mb-6 text-sm text-slate-500">{error}</p>
        <button
          onClick={clear}
          className="rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-medium text-slate-600 transition hover:border-red-200 hover:text-red-600"
        >
          پاک کردن مقایسه و شروع دوباره
        </button>
      </div>
    );
  }

  const specRows = specificationRows(products);
  const canAddMore = count < MAX_COMPARE_ITEMS;
  const shareCategory = products[0]?.category;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          مقایسه محصولات{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({products.length.toLocaleString("fa-IR")} از{" "}
            {MAX_COMPARE_ITEMS.toLocaleString("fa-IR")})
          </span>
        </h1>
        <div className="flex items-center gap-3">
          {canAddMore && shareCategory && (
            <Link
              href={`/category/${products[0].categorySlug}`}
              className="text-xs font-medium text-brand-600 hover:underline"
            >
              + افزودن محصول دیگر از {shareCategory}
            </Link>
          )}
          <button
            onClick={clear}
            className="rounded-lg px-3 py-2 text-xs font-medium text-slate-500 transition hover:bg-slate-100"
          >
            پاک کردن همه
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <tbody>
            <tr className="border-b border-slate-100">
              <th className="sticky right-0 z-10 w-36 bg-white p-4 text-right text-xs font-bold text-slate-500 sm:w-44">
                محصول
              </th>
              {products.map((product) => (
                <td key={product.id} className="min-w-48 p-4 align-top">
                  <div className="flex flex-col items-center gap-2 text-center">
                    <button
                      onClick={() => remove(product.id)}
                      aria-label={`حذف ${product.title} از مقایسه`}
                      title="حذف از مقایسه"
                      className="self-end text-xs text-slate-400 transition hover:text-red-500"
                    >
                      ✕
                    </button>
                    <Link
                      href={`/product/${product.id}`}
                      className="block h-24 w-24 overflow-hidden rounded-xl bg-slate-50"
                    >
                      {product.image ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={product.image}
                          alt={product.title}
                          className="h-full w-full object-cover"
                        />
                      ) : null}
                    </Link>
                    <Link
                      href={`/product/${product.id}`}
                      className="line-clamp-2 text-sm font-medium text-slate-700 hover:text-brand-700"
                    >
                      {product.title}
                    </Link>
                  </div>
                </td>
              ))}
            </tr>

            <tr className="border-b border-slate-100 bg-slate-50/50">
              <th className="sticky right-0 z-10 bg-slate-50/50 p-4 text-right text-xs font-medium text-slate-500">
                برند
              </th>
              {products.map((product) => (
                <td key={product.id} className="p-4 text-center text-slate-700">
                  {product.brand?.name ?? "—"}
                </td>
              ))}
            </tr>

            <tr className="border-b border-slate-100">
              <th className="sticky right-0 z-10 bg-white p-4 text-right text-xs font-medium text-slate-500">
                قیمت
              </th>
              {products.map((product) => (
                <td key={product.id} className="p-4 text-center">
                  <span className="font-num font-bold text-slate-800">
                    {formatPrice(product.price)}
                  </span>
                  <span className="mr-1 text-xs text-slate-400">تومان</span>
                  {product.oldPrice && (
                    <div className="mt-1 text-xs text-slate-300 line-through font-num">
                      {formatPrice(product.oldPrice)}
                    </div>
                  )}
                </td>
              ))}
            </tr>

            <tr className="border-b border-slate-100 bg-slate-50/50">
              <th className="sticky right-0 z-10 bg-slate-50/50 p-4 text-right text-xs font-medium text-slate-500">
                موجودی
              </th>
              {products.map((product) => (
                <td key={product.id} className="p-4 text-center">
                  {(product.stock ?? 0) > 0 ? (
                    <span className="rounded-md bg-brand-50 px-2 py-1 text-xs font-medium text-brand-700">
                      موجود
                    </span>
                  ) : (
                    <span className="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-600">
                      ناموجود
                    </span>
                  )}
                </td>
              ))}
            </tr>

            <tr className="border-b border-slate-100">
              <th className="sticky right-0 z-10 bg-white p-4 text-right text-xs font-medium text-slate-500">
                امتیاز
              </th>
              {products.map((product) => (
                <td key={product.id} className="p-4 text-center text-slate-700">
                  <span className="text-amber-400">★</span>{" "}
                  <span className="font-num">
                    {product.rating.toLocaleString("fa-IR")}
                  </span>{" "}
                  <span className="font-num text-xs text-slate-400">
                    ({product.ratingCount.toLocaleString("fa-IR")})
                  </span>
                </td>
              ))}
            </tr>

            <tr className="border-b border-slate-100 bg-slate-50/50">
              <th className="sticky right-0 z-10 bg-slate-50/50 p-4 text-right text-xs font-medium text-slate-500">
                گارانتی
              </th>
              {products.map((product) => (
                <td key={product.id} className="p-4 text-center text-slate-700">
                  {product.warranty || "—"}
                </td>
              ))}
            </tr>

            {specRows.map((row, index) => (
              <tr
                key={row.slug}
                className={`border-b border-slate-100 last:border-b-0 ${
                  index % 2 === 0 ? "bg-white" : "bg-slate-50/50"
                }`}
              >
                <th
                  className={`sticky right-0 z-10 p-4 text-right text-xs font-medium text-slate-500 ${
                    index % 2 === 0 ? "bg-white" : "bg-slate-50/50"
                  }`}
                >
                  {row.name}
                </th>
                {row.values.map((value, i) => (
                  <td key={products[i].id} className="p-4 text-center text-slate-700">
                    <bdi dir="auto">{value ?? "—"}</bdi>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
