"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ProductCard from "@/components/product/ProductCard";
import ProductRail from "@/components/product/ProductRail";
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
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-800">{title}</h2>
        <button
          type="button"
          onClick={() => {
            clearRecentlyViewed();
            setProducts([]);
          }}
          className="-my-2 inline-flex min-h-11 shrink-0 items-center px-1 text-xs text-slate-400 transition hover:text-red-500 sm:min-h-0 sm:py-0"
        >
          پاک کردن تاریخچه
        </button>
      </div>
      <ProductRail>
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </ProductRail>
    </section>
  );
}
