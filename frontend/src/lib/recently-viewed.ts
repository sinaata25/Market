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
        Number.isInteger(value) && typeof value === "number" && value > 0
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
  if (!Number.isInteger(productId) || productId < 1) return current;
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
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
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
    window.localStorage.removeItem(STORAGE_KEY);
    window.dispatchEvent(new CustomEvent(UPDATED_EVENT));
  } catch {
    // Clearing optional local history must not affect navigation.
  }
}

export function subscribeRecentlyViewed(callback: () => void): () => void {
  window.addEventListener(UPDATED_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(UPDATED_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}
