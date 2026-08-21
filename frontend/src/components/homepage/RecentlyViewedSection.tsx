"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ProductCard from "@/components/product/ProductCard";
import { api } from "@/lib/client-api";
import type { Product } from "@/lib/products";
import {
  clearRecentlyViewed,
  getRecentlyViewedIds,
  replaceRecentlyViewedIds,
  subscribeRecentlyViewed,
} from "@/lib/recently-viewed";

export default function RecentlyViewedSection({
  title,
  limit,
}: {
  title: string;
  limit: number;
}) {
  const [products, setProducts] = useState<Product[]>([]);
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const currentRequest = ++requestId.current;
    const ids = getRecentlyViewedIds();
    if (ids.length === 0) {
      setProducts([]);
      return;
    }
    const result = await api.get<{ items: Product[] }>(
      `/api/products/by-ids?ids=${ids.join(",")}`
    );
    if (requestId.current !== currentRequest) return;
    if (!result.ok || !result.data) {
      setProducts([]);
      return;
    }
    const currentProducts = result.data.items;
    setProducts(currentProducts.slice(0, limit));
    const validIds = currentProducts.map((product) => product.id);
    if (validIds.length !== ids.length) {
      replaceRecentlyViewedIds(validIds);
    }
  }, [limit]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    const unsubscribe = subscribeRecentlyViewed(() => void load());
    return () => {
      requestId.current += 1;
      window.clearTimeout(timer);
      unsubscribe();
    };
  }, [load]);

  if (products.length === 0) return null;

  return (
    <section className="min-w-0">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-lg font-bold text-slate-800">{title}</h2>
        <button
          type="button"
          onClick={() => {
            clearRecentlyViewed();
            setProducts([]);
          }}
          className="shrink-0 text-xs text-slate-400 transition hover:text-red-500"
        >
          پاک کردن تاریخچه
        </button>
      </div>
      <div className="max-w-full overflow-x-auto overscroll-x-contain pb-3">
        <div className="grid w-max grid-flow-col auto-cols-[10.5rem] gap-3 sm:auto-cols-[13rem] lg:auto-cols-[14rem]">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </div>
    </section>
  );
}
