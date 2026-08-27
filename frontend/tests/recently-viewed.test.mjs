import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  MAX_RECENTLY_VIEWED,
  clearRecentlyViewed,
  getRecentlyViewedIds,
  nextRecentlyViewedIds,
  parseRecentlyViewedIds,
  replaceRecentlyViewedIds,
  recordRecentlyViewed,
  subscribeRecentlyViewed,
  visibleRecentlyViewedProducts,
} from "../src/lib/recently-viewed.ts";

const source = (path) =>
  readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("one valid product view creates a one-item history", () => {
  assert.deepEqual(nextRecentlyViewedIds([], 42), [42]);
});

test("empty or unusable storage produces an empty history", () => {
  assert.deepEqual(parseRecentlyViewedIds(null), []);
  assert.deepEqual(parseRecentlyViewedIds("{}"), []);
});

test("new views are newest-first and revisits move without duplicates", () => {
  let ids = [];
  ids = nextRecentlyViewedIds(ids, 1);
  ids = nextRecentlyViewedIds(ids, 2);
  ids = nextRecentlyViewedIds(ids, 3);
  assert.deepEqual(ids, [3, 2, 1]);

  ids = nextRecentlyViewedIds(ids, 1);
  assert.deepEqual(ids, [1, 3, 2]);
});

test("history is capped at the single shared maximum", () => {
  let ids = [];
  for (let id = 1; id <= MAX_RECENTLY_VIEWED + 4; id += 1) {
    ids = nextRecentlyViewedIds(ids, id);
  }
  assert.equal(ids.length, MAX_RECENTLY_VIEWED);
  assert.equal(ids[0], MAX_RECENTLY_VIEWED + 4);
  assert.equal(ids.at(-1), 5);
});

test("stored history rejects malformed IDs and removes duplicates", () => {
  assert.deepEqual(parseRecentlyViewedIds('[3,2,3,-1,"4",null,1]'), [3, 2, 1]);
  assert.deepEqual(parseRecentlyViewedIds(`[${Number.MAX_SAFE_INTEGER + 1}]`), []);
  assert.deepEqual(parseRecentlyViewedIds("not json"), []);
});

test("the current product is hidden without changing the ordered history", () => {
  const products = [{ id: 3 }, { id: 2 }, { id: 1 }];

  assert.deepEqual(visibleRecentlyViewedProducts(products, 3, 15), [
    { id: 2 },
    { id: 1 },
  ]);
  assert.deepEqual(products, [{ id: 3 }, { id: 2 }, { id: 1 }]);
});

test("recent-history helpers are safe during server rendering", () => {
  assert.equal(typeof globalThis.window, "undefined");
  assert.deepEqual(getRecentlyViewedIds(), []);
  assert.doesNotThrow(() => replaceRecentlyViewedIds([1]));
  assert.doesNotThrow(() => recordRecentlyViewed(1));
  assert.doesNotThrow(() => clearRecentlyViewed());
  assert.doesNotThrow(() => subscribeRecentlyViewed(() => {})());
});

test("recorded IDs persist through a fresh storage read", () => {
  const values = new Map();
  globalThis.CustomEvent = class CustomEvent {};
  globalThis.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key),
    },
    dispatchEvent: () => {},
  };

  recordRecentlyViewed(7);
  recordRecentlyViewed(9);

  assert.deepEqual(getRecentlyViewedIds(), [9, 7]);
  clearRecentlyViewed();
  assert.deepEqual(getRecentlyViewedIds(), []);
  delete globalThis.window;
  delete globalThis.CustomEvent;
});

test("recording an unchanged newest product avoids redundant storage writes", () => {
  const values = new Map();
  let writes = 0;
  let events = 0;
  globalThis.CustomEvent = class CustomEvent {};
  globalThis.window = {
    localStorage: {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => {
        writes += 1;
        values.set(key, value);
      },
      removeItem: (key) => values.delete(key),
    },
    dispatchEvent: () => {
      events += 1;
    },
  };

  recordRecentlyViewed(7);
  recordRecentlyViewed(7);

  assert.equal(writes, 1);
  assert.equal(events, 1);
  delete globalThis.window;
  delete globalThis.CustomEvent;
});

test("product, category, and brand pages render the shared recent section", async () => {
  const [productPage, categoryPage, brandPage] = await Promise.all([
    source("src/app/product/[id]/page.tsx"),
    source("src/app/category/[slug]/page.tsx"),
    source("src/app/brand/[slug]/page.tsx"),
  ]);

  assert.match(productPage, /<RecentlyViewedTracker productId=\{product\.id\}/);
  assert.match(productPage, /<RecentlyViewedSection[\s\S]*excludeProductId=\{product\.id\}/);
  assert.match(categoryPage, /<RecentlyViewedSection className="mt-12"/);
  assert.match(brandPage, /<RecentlyViewedSection className="mt-12"/);
  assert.ok(
    categoryPage.indexOf("سایر دسته‌بندی‌ها") <
      categoryPage.indexOf("<RecentlyViewedSection")
  );
  assert.ok(
    brandPage.indexOf("سایر برندها") <
      brandPage.indexOf("<RecentlyViewedSection")
  );
});

test("the shared section batches fresh data, hides empty history, and reuses responsive cards", async () => {
  const [section, grid, rail] = await Promise.all([
    source("src/components/product/RecentlyViewedSection.tsx"),
    source("src/components/product/ProductGrid.tsx"),
    source("src/components/product/ProductRail.tsx"),
  ]);

  assert.match(section, /\/api\/products\/by-ids\?ids=/);
  assert.match(section, /if \(visibleProducts\.length === 0\) return null/);
  assert.match(section, /<ProductRail>/);
  assert.match(section, /<ProductCard key=\{product\.id\} product=\{product\}/);
  assert.match(rail, /overflow-x-auto/);
  assert.match(grid, /auto-cols-\[10\.5rem\]/);
  assert.match(grid, /sm:grid-cols-3/);
  assert.match(grid, /xl:grid-cols-5/);
});
