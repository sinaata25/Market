import assert from "node:assert/strict";
import test from "node:test";

import {
  footerColumnGridClass,
  footerIconSource,
  footerLinkAttributes,
  partitionFooterSections,
} from "../src/lib/footer-layout.ts";

const link = (overrides = {}) => ({
  url: "/support",
  isExternal: false,
  openInNewTab: false,
  ...overrides,
});

test("the current three-column footer keeps its four-column desktop grid", () => {
  // ستون معرفی برند + سه بخش مدیر — همان چیدمانی که فوتر امروز دارد
  assert.equal(footerColumnGridClass(3), "lg:grid-cols-4");
});

test("adding sections wraps after four desktop columns instead of squashing them", () => {
  assert.equal(footerColumnGridClass(4), "lg:grid-cols-4");
  assert.equal(footerColumnGridClass(8), "lg:grid-cols-4");
});

test("small and unusual section counts always produce a valid desktop grid", () => {
  assert.equal(footerColumnGridClass(0), "lg:grid-cols-1");
  assert.equal(footerColumnGridClass(1), "lg:grid-cols-2");
  assert.equal(footerColumnGridClass(2), "lg:grid-cols-3");
  assert.equal(footerColumnGridClass(99), "lg:grid-cols-4");
  assert.equal(footerColumnGridClass(-1), "lg:grid-cols-1");
});

test("an item with no destination gets no link attributes", () => {
  assert.equal(footerLinkAttributes(link({ url: null })), null);
  assert.equal(footerLinkAttributes(link({ url: "   " })), null);
});

test("an internal link is rendered through the client-side router", () => {
  const attributes = footerLinkAttributes(link());
  assert.equal(attributes.href, "/support");
  assert.equal(attributes.external, false);
  assert.equal(attributes.target, undefined);
});

test("an external link opened in a new tab cannot reach window.opener", () => {
  const attributes = footerLinkAttributes(
    link({ url: "https://instagram.com/shop", isExternal: true, openInNewTab: true })
  );
  assert.equal(attributes.external, true);
  assert.equal(attributes.target, "_blank");
  assert.equal(attributes.rel, "noopener noreferrer");
});

test("an internal link in a new tab needs no rel — there is no cross-origin opener", () => {
  const attributes = footerLinkAttributes(link({ openInNewTab: true }));
  assert.equal(attributes.target, "_blank");
  assert.equal(attributes.rel, undefined);
});

test("strips are separated from columns while each keeps the admin's order", () => {
  const { strips, columns } = partitionFooterSections([
    { id: 1, variant: "strip" },
    { id: 2, variant: "column" },
    { id: 3, variant: "column" },
    { id: 4, variant: "strip" },
  ]);
  assert.deepEqual(
    strips.map((section) => section.id),
    [1, 4]
  );
  assert.deepEqual(
    columns.map((section) => section.id),
    [2, 3]
  );
});

test("a section variant the frontend does not know yet still renders as a column", () => {
  const { columns } = partitionFooterSections([{ id: 1, variant: "newsletter" }]);
  assert.deepEqual(
    columns.map((section) => section.id),
    [1]
  );
});

test("an uploaded icon file always wins over the emoji fallback", () => {
  assert.deepEqual(footerIconSource("/media/footer/icons/delivery.svg", "🚚"), {
    kind: "image",
    value: "/media/footer/icons/delivery.svg",
  });
});

test("the emoji is used only when no icon file is selected", () => {
  assert.deepEqual(footerIconSource(null, "🚚"), { kind: "emoji", value: "🚚" });
  assert.deepEqual(footerIconSource("", "🚚"), { kind: "emoji", value: "🚚" });
  assert.deepEqual(footerIconSource("   ", "🚚"), { kind: "emoji", value: "🚚" });
});

test("with neither an icon nor an emoji, nothing is rendered", () => {
  assert.deepEqual(footerIconSource(null, null), { kind: "none" });
  assert.deepEqual(footerIconSource(undefined), { kind: "none" });
  assert.deepEqual(footerIconSource("", "  "), { kind: "none" });
});
