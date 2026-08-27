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
  visibleRecentlyViewedProducts,
} from "@/lib/recently-viewed";

type RecentlyViewedSectionProps = {
  title?: string;
  limit?: number;
  excludeProductId?: number;
  className?: string;
};

const DEFAULT_VISIBLE_PRODUCTS = 5;

export default function RecentlyViewedSection({
  title = "محصولات اخیراً مشاهده‌شده",
  limit = DEFAULT_VISIBLE_PRODUCTS,
  excludeProductId,
  className = "",
}: RecentlyViewedSectionProps) {
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
    const validIds = currentProducts.map((product) => product.id);
    setProducts(currentProducts);

    // Keep the current product in history while removing deleted/inactive IDs.
    if (
      validIds.length !== ids.length ||
      validIds.some((productId, index) => productId !== ids[index])
    ) {
      replaceRecentlyViewedIds(validIds);
    }
  }, []);

  useEffect(() => {
    // Deferring the first read lets the product-page tracker record its ID first.
    const timer = window.setTimeout(() => void load(), 0);
    const unsubscribe = subscribeRecentlyViewed(() => void load());
    return () => {
      requestId.current += 1;
      window.clearTimeout(timer);
      unsubscribe();
    };
  }, [load]);

  const visibleProducts = visibleRecentlyViewedProducts(
    products,
    excludeProductId,
    limit
  );
  if (visibleProducts.length === 0) return null;

  return (
    <section className={`min-w-0 ${className}`}>
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
        {visibleProducts.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </ProductRail>
    </section>
  );
}
