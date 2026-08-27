import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = (path) =>
  readFile(new URL(`../${path}`, import.meta.url), "utf8");

test("the responsive header search submits a bounded URL query and can clear it", async () => {
  const search = await source("src/components/layout/HeaderSearch.tsx");
  const header = await source("src/components/layout/Header.tsx");

  assert.match(search, /<form onSubmit=\{submit\} role="search"/);
  assert.match(search, /new URLSearchParams\(\)/);
  assert.match(search, /router\.push\(`\/products/);
  assert.match(search, /maxLength=\{200\}/);
  assert.match(search, /params\.delete\("search"\)/);
  assert.match(header, /<Suspense fallback=\{<HeaderSearchFallback \/>\}>/);
});

test("public product searches expose route loading and result error states", async () => {
  const products = await source("src/app/products/page.tsx");
  const category = await source("src/app/category/[slug]/page.tsx");
  const productsLoading = await source("src/app/products/loading.tsx");
  const categoryLoading = await source("src/app/category/[slug]/loading.tsx");

  assert.match(products, /productsFailed/);
  assert.match(products, /دریافت نتایج جستجو ممکن نشد/);
  assert.match(category, /productsFailed/);
  assert.match(category, /دریافت نتایج جستجو ممکن نشد/);
  assert.match(productsLoading, /ProductListingLoading/);
  assert.match(categoryLoading, /ProductListingLoading/);
});

test("live admin list searches debounce and reject stale responses", async () => {
  const paths = [
    "src/app/admin/products/page.tsx",
    "src/app/admin/orders/page.tsx",
    "src/app/admin/users/page.tsx",
    "src/app/admin/blog/page.tsx",
    "src/app/admin/seo/pages/page.tsx",
  ];

  for (const path of paths) {
    const page = await source(path);
    assert.match(page, /useDebouncedValue\(search\)/, path);
    assert.match(page, /\+\+requestId\.current/, path);
    assert.match(page, /currentRequest !== requestId\.current/, path);
    assert.match(page, /type="search"/, path);
    assert.match(page, /setPage\(1\)/, path);
  }
});

test("SEO page inventory search is API-backed and paginated", async () => {
  const page = await source("src/app/admin/seo/pages/page.tsx");

  assert.match(page, /query\.set\("search", debouncedSearch\.trim\(\)\)/);
  assert.match(page, /query\.set\("type", filter\)/);
  assert.match(page, /<Pager\s+page=\{page\}\s+pages=\{pageCount\}/);
  assert.doesNotMatch(page, /pages\.filter\(/);
});

test("local FAQ search uses shared Persian normalization and an explicit clear action", async () => {
  const support = await source("src/components/static-pages/SupportContent.tsx");
  const helper = await source("src/lib/search.ts");

  assert.match(support, /normalizeSearchText\(query\)/);
  assert.match(support, /searchTextIncludes/);
  assert.match(support, /aria-label="پاک کردن جستجو"/);
  assert.match(helper, /replace\(\/\[يى\]\/gu, "ی"\)/);
  assert.match(helper, /replace\(\/ك\/gu, "ک"\)/);
});
