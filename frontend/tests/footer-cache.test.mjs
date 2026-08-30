import assert from "node:assert/strict";
import test from "node:test";

import {
  FOOTER_CACHE_SECONDS,
  FOOTER_CACHE_TAG,
  footerFetchOptions,
} from "../src/lib/footer-cache.ts";

test("in development the footer is never cached, so an admin edit shows on the next reload", () => {
  for (const env of ["development", "test", undefined]) {
    const options = footerFetchOptions(env);
    assert.equal(options.cache, "no-store");
    assert.equal(options.next, undefined);
  }
});

test("in production the footer is cached and tagged for on-demand invalidation", () => {
  const options = footerFetchOptions("production");
  assert.equal(options.cache, "force-cache");
  assert.deepEqual(options.next.tags, [FOOTER_CACHE_TAG]);
  assert.equal(options.next.revalidate, FOOTER_CACHE_SECONDS);
});

test("the unconfigured-webhook fallback window stays short enough to not look broken", () => {
  assert.ok(FOOTER_CACHE_SECONDS > 0);
  assert.ok(FOOTER_CACHE_SECONDS <= 60);
});

test("cache options never combine no-store with a revalidate window", () => {
  // Next این ترکیب را متناقض می‌داند و هر دو را نادیده می‌گیرد
  for (const env of ["development", "production"]) {
    const options = footerFetchOptions(env);
    assert.ok(!(options.cache === "no-store" && options.next));
  }
});
