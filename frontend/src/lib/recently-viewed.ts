"use client";

const STORAGE_KEY = "market:recently-viewed:v1";
const UPDATED_EVENT = "recently-viewed:updated";
export const MAX_RECENTLY_VIEWED = 15;

export function parseRecentlyViewedIds(raw: string | null): number[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const ids = parsed.filter(
      (value): value is number =>
        typeof value === "number" &&
        Number.isSafeInteger(value) &&
        value > 0
    );
    return [...new Set(ids)].slice(0, MAX_RECENTLY_VIEWED);
  } catch {
    return [];
  }
}

export function nextRecentlyViewedIds(
  current: number[],
  productId: number
): number[] {
  if (!Number.isSafeInteger(productId) || productId < 1) return current;
  return [productId, ...current.filter((id) => id !== productId)].slice(
    0,
    MAX_RECENTLY_VIEWED
  );
}

export function getRecentlyViewedIds(): number[] {
  if (typeof window === "undefined") return [];
  try {
    return parseRecentlyViewedIds(window.localStorage.getItem(STORAGE_KEY));
  } catch {
    return [];
  }
}

export function replaceRecentlyViewedIds(ids: number[]): void {
  if (typeof window === "undefined") return;
  const normalized = parseRecentlyViewedIds(JSON.stringify(ids));
  try {
    const serialized = JSON.stringify(normalized);
    if (window.localStorage.getItem(STORAGE_KEY) === serialized) return;
    window.localStorage.setItem(STORAGE_KEY, serialized);
    window.dispatchEvent(new CustomEvent(UPDATED_EVENT));
  } catch {
    // Storage can be disabled or full; browsing must continue normally.
  }
}

export function recordRecentlyViewed(productId: number): void {
  replaceRecentlyViewedIds(nextRecentlyViewedIds(getRecentlyViewedIds(), productId));
}

export function clearRecentlyViewed(): void {
  if (typeof window === "undefined") return;
  try {
    if (window.localStorage.getItem(STORAGE_KEY) === null) return;
    window.localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new CustomEvent(UPDATED_EVENT));
  } catch {
    // Clearing optional local history must not affect navigation.
  }
}

export function subscribeRecentlyViewed(callback: () => void): () => void {
  if (typeof window === "undefined") return () => {};

  const handleStorage = (event: StorageEvent) => {
    if (event.key === null || event.key === STORAGE_KEY) callback();
  };
  window.addEventListener(UPDATED_EVENT, callback);
  window.addEventListener("storage", handleStorage);
  return () => {
    window.removeEventListener(UPDATED_EVENT, callback);
    window.removeEventListener("storage", handleStorage);
  };
}

export function visibleRecentlyViewedProducts<T extends { id: number }>(
  products: T[],
  excludeProductId: number | undefined,
  limit: number
): T[] {
  const safeLimit =
    Number.isSafeInteger(limit) && limit > 0
      ? Math.min(limit, MAX_RECENTLY_VIEWED)
      : MAX_RECENTLY_VIEWED;
  return products
    .filter((product) => product.id !== excludeProductId)
    .slice(0, safeLimit);
}
