import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_RECENTLY_VIEWED,
  clearRecentlyViewed,
  getRecentlyViewedIds,
  nextRecentlyViewedIds,
  parseRecentlyViewedIds,
  recordRecentlyViewed,
} from "../src/lib/recently-viewed.ts";

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
  assert.deepEqual(parseRecentlyViewedIds("not json"), []);
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
