"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import type { Product } from "@/lib/products";
import ProductCard from "@/components/product/ProductCard";
import { faNum } from "@/components/admin/ui";

export default function MyFavorites() {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.get<{ favorites: Product[] }>("/api/auth/favorites").then((res) => {
      if (res.ok && res.data) setItems(res.data.favorites);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function remove(p: Product) {
    await api.post("/api/auth/favorites", { productId: p.id });
    setItems((prev) => prev.filter((i) => i.id !== p.id));
  }

  if (loading) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">
        علاقه‌مندی‌ها{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({faNum(items.length)})
        </span>
      </h1>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-5xl">❤️</span>
          <p className="mb-2 text-sm font-bold text-slate-700">
            لیست علاقه‌مندی‌های شما خالی است
          </p>
          <p className="mb-6 text-xs text-slate-500">
            با زدن آیکون ❤️ در صفحه محصول، آن را اینجا ذخیره کنید.
          </p>
          <Link
            href="/"
            className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مشاهده محصولات
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {items.map((p) => (
            <div key={p.id} className="relative">
              <ProductCard product={p} />
              <button
                onClick={() => remove(p)}
                title="حذف از علاقه‌مندی‌ها"
                className="absolute left-4 top-4 z-10 grid h-8 w-8 place-items-center rounded-full bg-white/90 text-sm shadow-sm backdrop-blur transition hover:bg-red-50"
              >
                🗑
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
