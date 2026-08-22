import assert from "node:assert/strict";
import test from "node:test";

import {
  cityOptionLabel,
  createLocationsApi,
  locationAfterProvinceChange,
  normalizeLocationName,
  PROVINCES_API_PATH,
  provinceCitiesApiPath,
  resolveLocationOption,
} from "../src/lib/location-options.ts";

const PROVINCES = [
  { id: "07", name: "فارس" },
  { id: "23", name: "تهران" },
];

const CITIES = [
  { id: "0701", name: "علی آباد", countyName: "اول" },
  { id: "0702", name: "علی آباد", countyName: "دوم" },
  { id: "0703", name: "شیراز", countyName: "شیراز" },
];

test("province changes preserve the official string ID and reset city", () => {
  assert.deepEqual(locationAfterProvinceChange(PROVINCES, "07"), {
    province: "فارس",
    city: "",
    provinceId: "07",
    cityId: null,
  });
});

test("legacy names hydrate only when they identify one option", () => {
  assert.deepEqual(resolveLocationOption(PROVINCES, null, "فارس"), {
    id: "07",
    name: "فارس",
  });
  assert.equal(resolveLocationOption(CITIES, null, "علی آباد"), null);
  assert.equal(resolveLocationOption(CITIES, "0702", "علی آباد")?.id, "0702");
});

test("legacy matching mirrors backend Persian and whitespace normalization", () => {
  assert.equal(normalizeLocationName("  كِيشـ  "), "کیش");
  assert.equal(normalizeLocationName("نيم\u200cروز"), "نیم\u200cروز");
  assert.equal(
    resolveLocationOption([{ id: "01", name: "کیش" }], null, " كِيش ")?.id,
    "01"
  );
});

test("county is shown only when same-name cities need disambiguation", () => {
  assert.equal(
    cityOptionLabel(CITIES[0], CITIES),
    "علی آباد — شهرستان اول"
  );
  assert.equal(cityOptionLabel(CITIES[2], CITIES), "شیراز");
});

test("location API paths keep leading zeroes and omit trailing slashes", () => {
  assert.equal(PROVINCES_API_PATH, "/api/locations/provinces");
  assert.equal(
    provinceCitiesApiPath("07"),
    "/api/locations/provinces/07/cities"
  );
});

test("successful and in-flight location requests are deduplicated", async () => {
  const calls = [];
  const locationApi = createLocationsApi(async (path) => {
    calls.push(path);
    await Promise.resolve();
    return path === PROVINCES_API_PATH
      ? { ok: true, data: { provinces: PROVINCES }, status: 200 }
      : {
          ok: true,
          data: { province: PROVINCES[0], cities: CITIES },
          status: 200,
        };
  });

  await Promise.all([
    locationApi.getProvinces(),
    locationApi.getProvinces(),
    locationApi.getCities("07"),
    locationApi.getCities("07"),
  ]);
  await locationApi.getProvinces();
  await locationApi.getCities("07");

  assert.deepEqual(calls, [
    "/api/locations/provinces",
    "/api/locations/provinces/07/cities",
  ]);
});

test("failed requests are retried and force refresh bypasses cached success", async () => {
  let calls = 0;
  const locationApi = createLocationsApi(async () => {
    calls += 1;
    if (calls === 1) {
      return { ok: false, error: "خطا", status: 503 };
    }
    return { ok: true, data: { provinces: PROVINCES }, status: 200 };
  });

  assert.equal((await locationApi.getProvinces()).ok, false);
  assert.equal((await locationApi.getProvinces()).ok, true);
  assert.equal((await locationApi.getProvinces()).ok, true);
  assert.equal(calls, 2);

  assert.equal(
    (await locationApi.getProvinces({ force: true })).ok,
    true
  );
  assert.equal(calls, 3);
});
