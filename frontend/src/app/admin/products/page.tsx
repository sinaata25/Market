"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { formatPrice, type Product } from "@/lib/products";
import { faNum, Pager, EmptyRow } from "@/components/admin/ui";

export default function AdminProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    const qs = new URLSearchParams({ page: String(page) });
    if (search.trim()) qs.set("search", search.trim());
    api
      .get<{ products: Product[]; pages: number; total: number }>(
        `/api/admin/products?${qs}`
      )
      .then((res) => {
        if (res.ok && res.data) {
          setProducts(res.data.products);
          setPages(res.data.pages);
          setTotal(res.data.total);
        }
        setLoading(false);
      });
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(p: Product) {
    if (!confirm(`محصول «${p.title}» حذف شود؟`)) return;
    const res = await api.delete(`/api/admin/products/${p.id}`);
    if (res.ok) {
      setMessage("محصول حذف شد ✅");
      load();
    } else {
      setMessage(res.error ?? "خطا در حذف");
    }
    setTimeout(() => setMessage(""), 4000);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          محصولات{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(total)})
          </span>
        </h1>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="جستجوی محصول..."
            className="w-48 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400"
          />
          <Link
            href="/admin/products/new"
            className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-brand-700"
          >
            + افزودن محصول
          </Link>
        </div>
      </div>

      {message && (
        <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">
          {message}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">محصول</th>
              <th className="px-3 py-3 font-medium">دسته</th>
              <th className="px-3 py-3 font-medium">قیمت (تومان)</th>
              <th className="px-3 py-3 font-medium">موجودی</th>
              <th className="px-3 py-3 font-medium">امتیاز</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={6} text="در حال بارگذاری..." />
            ) : products.length === 0 ? (
              <EmptyRow colSpan={6} text="محصولی یافت نشد" />
            ) : (
              products.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-lg bg-slate-50 text-xl">
                        {p.image ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={p.image}
                            alt=""
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          p.emoji
                        )}
                      </span>
                      <div className="min-w-0">
                        <p className="max-w-[220px] truncate text-xs text-slate-700">
                          {p.title}
                        </p>
                        {p.badge && (
                          <span className="mt-1 inline-block rounded bg-brand-50 px-1.5 py-0.5 text-[10px] text-brand-700">
                            {p.badge}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500">
                    {p.category}
                  </td>
                  <td className="px-3 py-3">
                    <p className="text-xs font-bold text-slate-700 font-num">
                      {formatPrice(p.price)}
                    </p>
                    {p.oldPrice && (
                      <p className="text-[10px] text-slate-300 line-through font-num">
                        {formatPrice(p.oldPrice)}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`rounded-md px-2 py-1 text-[11px] font-bold font-num ${
                        (p.stock ?? 0) === 0
                          ? "bg-red-50 text-red-500"
                          : (p.stock ?? 0) <= 5
                            ? "bg-amber-50 text-amber-600"
                            : "bg-emerald-50 text-emerald-600"
                      }`}
                    >
                      {faNum(p.stock ?? 0)}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500 font-num">
                    ★ {faNum(p.rating)}{" "}
                    <span className="text-slate-300">({faNum(p.ratingCount)})</span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3 text-xs">
                      <Link
                        href={`/admin/products/${p.id}`}
                        className="text-brand-600 hover:underline"
                      >
                        ویرایش
                      </Link>
                      <button
                        onClick={() => remove(p)}
                        className="text-red-400 hover:text-red-600"
                      >
                        حذف
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pager page={page} pages={pages} onPage={setPage} />
    </div>
  );
}
