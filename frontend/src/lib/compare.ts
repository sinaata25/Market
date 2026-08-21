"use client";

import { useCallback, useSyncExternalStore } from "react";
import type { Product } from "@/lib/products";

// وضعیت مقایسه‌ی محصولات — کاملاً سمت کلاینت (localStorage)، بدون نیاز به مدل دیتابیس.
// حداکثر ۵ محصول از یک دسته‌بندی مشترک؛ سرور هم همین قانون را در POST /api/products/compare بازبینی می‌کند.

export type CompareItem = {
  id: number;
  title: string;
  image?: string | null;
  price: number;
  categorySlugs: string[];
};

export type CompareCheck = { ok: boolean; reason?: string };

const STORAGE_KEY = "market:compare";
const EVENT = "compare:updated";
export const MAX_COMPARE_ITEMS = 5;
export const MIN_COMPARE_ITEMS = 2;

function parseItems(raw: string | null): CompareItem[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function readItems(): CompareItem[] {
  if (typeof window === "undefined") return [];
  return parseItems(window.localStorage.getItem(STORAGE_KEY));
}

function writeItems(items: CompareItem[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new CustomEvent(EVENT));
}

// کش برای useSyncExternalStore — همان مرجع آرایه را برمی‌گرداند مگر داده واقعاً تغییر کرده باشد
const EMPTY: CompareItem[] = [];
let cachedRaw: string | null = null;
let cachedItems: CompareItem[] = EMPTY;

function getSnapshot(): CompareItem[] {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === cachedRaw) return cachedItems;
  cachedRaw = raw;
  cachedItems = parseItems(raw);
  return cachedItems;
}

function getServerSnapshot(): CompareItem[] {
  return EMPTY;
}

function subscribe(callback: () => void): () => void {
  window.addEventListener(EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

function intersect(a: string[], b: string[]): string[] {
  const setB = new Set(b);
  return a.filter((slug) => setB.has(slug));
}

// دسته‌بندی‌های مشترک بین همه‌ی محصولات فعلی مقایسه (برای اعتبارسنجی افزودن محصول بعدی کافی است)
export function commonCategorySlugs(items: CompareItem[]): string[] {
  if (items.length === 0) return [];
  return items
    .slice(1)
    .reduce((common, item) => intersect(common, item.categorySlugs), items[0].categorySlugs);
}

function toCompareItem(product: Product): CompareItem {
  return {
    id: product.id,
    title: product.title,
    image: product.image ?? null,
    price: product.price,
    categorySlugs:
      product.categorySlugs ?? (product.categorySlug ? [product.categorySlug] : []),
  };
}

export function getCompareItems(): CompareItem[] {
  return readItems();
}

export function isInCompare(productId: number): boolean {
  return readItems().some((item) => item.id === productId);
}

export function canAddToCompare(
  items: CompareItem[],
  product: Product
): CompareCheck {
  if (items.some((item) => item.id === product.id)) {
    return { ok: false, reason: "این محصول قبلاً به مقایسه اضافه شده است" };
  }
  if (items.length >= MAX_COMPARE_ITEMS) {
    return {
      ok: false,
      reason: `حداکثر ${MAX_COMPARE_ITEMS} محصول را می‌توان هم‌زمان مقایسه کرد`,
    };
  }
  if (items.length > 0) {
    const common = commonCategorySlugs(items);
    const candidateSlugs = toCompareItem(product).categorySlugs;
    if (intersect(common, candidateSlugs).length === 0) {
      return {
        ok: false,
        reason: "این محصول با دسته‌بندی محصولات انتخاب‌شده برای مقایسه سازگار نیست",
      };
    }
  }
  return { ok: true };
}

export function addToCompare(product: Product): CompareCheck {
  const items = readItems();
  const check = canAddToCompare(items, product);
  if (!check.ok) return check;
  writeItems([...items, toCompareItem(product)]);
  return { ok: true };
}

export function removeFromCompare(productId: number) {
  writeItems(readItems().filter((item) => item.id !== productId));
}

export function replaceInCompare(
  productId: number,
  product: Product
): CompareCheck {
  const remaining = readItems().filter((item) => item.id !== productId);
  const check = canAddToCompare(remaining, product);
  if (!check.ok) return check;
  writeItems([...remaining, toCompareItem(product)]);
  return { ok: true };
}

export function clearCompare() {
  writeItems([]);
}

export function useCompare() {
  const items = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const add = useCallback((product: Product) => addToCompare(product), []);
  const remove = useCallback((productId: number) => removeFromCompare(productId), []);
  const replace = useCallback(
    (productId: number, product: Product) => replaceInCompare(productId, product),
    []
  );
  const clear = useCallback(() => clearCompare(), []);
  const check = useCallback(
    (product: Product) => canAddToCompare(items, product),
    [items]
  );

  return {
    items,
    count: items.length,
    isFull: items.length >= MAX_COMPARE_ITEMS,
    canCompare: items.length >= MIN_COMPARE_ITEMS,
    add,
    remove,
    replace,
    clear,
    check,
  };
}
