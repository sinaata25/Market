import assert from "node:assert/strict";
import test from "node:test";

import {
  BANNER_DESKTOP_MEDIA,
  bannerImageSources,
} from "../src/lib/banner-image.ts";

test("a banner with no image at all has no sources", () => {
  assert.equal(
    bannerImageSources({ desktopImage: null, mobileImage: null }),
    null
  );
});

test("both variants: the desktop file is behind a min-width media query", () => {
  const sources = bannerImageSources({
    desktopImage: "/media/banners/wide.png",
    mobileImage: "/media/banners/mobile/narrow.png",
  });

  assert.equal(sources.desktop, "/media/banners/wide.png");
  assert.equal(sources.fallback, "/media/banners/mobile/narrow.png");
  assert.equal(sources.media, BANNER_DESKTOP_MEDIA);
});

test("the breakpoint matches the md breakpoint the project already uses", () => {
  assert.equal(BANNER_DESKTOP_MEDIA, "(min-width: 48rem)");
});

test("mobile is never a resize of desktop — each variant keeps its own file", () => {
  const sources = bannerImageSources({
    desktopImage: "/media/banners/wide.png",
    mobileImage: "/media/banners/mobile/narrow.png",
  });

  assert.notEqual(sources.desktop, sources.fallback);
});

test("only a desktop image: it is shown everywhere and no source is emitted", () => {
  const sources = bannerImageSources({
    desktopImage: "/media/banners/wide.png",
    mobileImage: null,
  });

  // بدون <source>، مرورگر فقط همین یک فایل را دانلود می‌کند
  assert.equal(sources.desktop, null);
  assert.equal(sources.fallback, "/media/banners/wide.png");
});

test("only a mobile image: it is shown everywhere and no source is emitted", () => {
  const sources = bannerImageSources({
    desktopImage: null,
    mobileImage: "/media/banners/mobile/narrow.png",
  });

  assert.equal(sources.desktop, null);
  assert.equal(sources.fallback, "/media/banners/mobile/narrow.png");
});

test("empty strings from the API count as missing images", () => {
  assert.equal(bannerImageSources({ desktopImage: "", mobileImage: "" }), null);

  const sources = bannerImageSources({
    desktopImage: "",
    mobileImage: "/media/banners/mobile/narrow.png",
  });
  assert.equal(sources.desktop, null);
  assert.equal(sources.fallback, "/media/banners/mobile/narrow.png");
});
