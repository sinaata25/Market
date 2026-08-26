import assert from "node:assert/strict";
import test from "node:test";

import { sectionAllLink } from "../src/lib/homepage-links.ts";

test("a brand row links to that brand's product listing", () => {
  assert.equal(
    sectionAllLink({ type: "brand_products", data: { brand: { slug: "ronix" } } }),
    "/brand/ronix"
  );
});

test("a category row links to that category's product listing", () => {
  assert.equal(
    sectionAllLink({
      type: "category_products",
      data: { category: { slug: "power-tools" } },
    }),
    "/category/power-tools"
  );
});

test("switching the selected brand moves the view-all link with it", () => {
  const section = { type: "brand_products", data: { brand: { slug: "ronix" } } };
  assert.equal(sectionAllLink(section), "/brand/ronix");

  const switched = { ...section, data: { brand: { slug: "bosch" } } };
  assert.equal(sectionAllLink(switched), "/brand/bosch");
});

test("a row whose reference is missing gets no view-all link", () => {
  assert.equal(sectionAllLink({ type: "brand_products", data: {} }), null);
  assert.equal(sectionAllLink({ type: "category_products", data: {} }), null);
});

test("the existing fixed section links still resolve", () => {
  assert.equal(sectionAllLink({ type: "best_sellers", data: {} }), "/best-sellers");
  assert.equal(sectionAllLink({ type: "incredible_products", data: {} }), "/incredible");
  assert.equal(sectionAllLink({ type: "discounted_products", data: {} }), "/discounts");
});

test("sections without a listing page have no view-all link", () => {
  assert.equal(sectionAllLink({ type: "new_products", data: {} }), null);
  assert.equal(sectionAllLink({ type: "product_collection", data: {} }), null);
});
