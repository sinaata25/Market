import assert from "node:assert/strict";
import test from "node:test";

import {
  MAP_ASPECT_RATIO,
  coordinateQuery,
  googleMapsEmbedUrl,
  shopLocationToRender,
} from "../src/lib/footer-map.ts";

const TEHRAN = { latitude: "35.715298", longitude: "51.404343", zoom: 15 };

test("the map destination is built from the saved coordinates", () => {
  assert.equal(coordinateQuery(TEHRAN), "35.715298,51.404343");
});

test("a negative or whole-number coordinate survives intact", () => {
  assert.equal(
    coordinateQuery({ latitude: "-33.86", longitude: "151", zoom: 15 }),
    "-33.86,151"
  );
});

test("coordinates outside the world produce no destination", () => {
  for (const location of [
    { latitude: "91", longitude: "51", zoom: 15 },
    { latitude: "35", longitude: "181", zoom: 15 },
    { latitude: "", longitude: "51", zoom: 15 },
    { latitude: "abc", longitude: "51", zoom: 15 },
  ]) {
    assert.equal(coordinateQuery(location), null);
    assert.equal(googleMapsEmbedUrl(location), null);
  }
});

test("without an API key the free keyless embed is used", () => {
  const url = new URL(googleMapsEmbedUrl(TEHRAN));
  assert.equal(url.hostname, "www.google.com");
  assert.equal(url.pathname, "/maps");
  assert.equal(url.searchParams.get("q"), "35.715298,51.404343");
  assert.equal(url.searchParams.get("output"), "embed");
  assert.equal(url.searchParams.get("z"), "15");
  assert.equal(url.searchParams.get("hl"), "fa");
});

test("an API key switches to the supported Maps Embed API", () => {
  const url = new URL(googleMapsEmbedUrl(TEHRAN, "test-key"));
  assert.equal(url.pathname, "/maps/embed/v1/place");
  assert.equal(url.searchParams.get("key"), "test-key");
  assert.equal(url.searchParams.get("q"), "35.715298,51.404343");
  assert.equal(url.searchParams.get("zoom"), "15");
});

test("an empty key string does not switch to the keyed endpoint", () => {
  assert.equal(new URL(googleMapsEmbedUrl(TEHRAN, "")).pathname, "/maps");
});

test("an out-of-range zoom is clamped instead of reaching Google", () => {
  const tooFar = new URL(googleMapsEmbedUrl({ ...TEHRAN, zoom: 99 }));
  const tooClose = new URL(googleMapsEmbedUrl({ ...TEHRAN, zoom: -4 }));
  assert.equal(tooFar.searchParams.get("z"), "21");
  assert.equal(tooClose.searchParams.get("z"), "1");
});

test("the map frame reserves a fixed aspect ratio so the footer cannot shift", () => {
  assert.equal(MAP_ASPECT_RATIO, "16 / 10");
});

test("the footer renders the location section when the map is enabled", () => {
  const location = {
    address: "تهران، آزادی",
    latitude: "35.715298",
    longitude: "51.404343",
    zoom: 15,
    mapsUrl: "https://www.google.com/maps/search/?api=1&query=35.715298%2C51.404343",
    directionsUrl: "https://www.google.com/maps/dir/?api=1&destination=35.715298%2C51.404343",
  };
  assert.equal(shopLocationToRender(location), location);
});

test("the footer renders no location section when the admin disabled the map", () => {
  // بک‌اند در آن حالت اصلاً بلوک موقعیت را نمی‌فرستد
  assert.equal(shopLocationToRender(null), null);
  assert.equal(shopLocationToRender(undefined), null);
});

test("a corrupt coordinate never renders a pin at the null island", () => {
  assert.equal(
    shopLocationToRender({ latitude: "", longitude: "", zoom: 15 }),
    null
  );
  assert.equal(
    shopLocationToRender({ latitude: "999", longitude: "51", zoom: 15 }),
    null
  );
});
