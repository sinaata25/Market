import assert from "node:assert/strict";
import test from "node:test";

import {
  adminRedirectFor,
  isDeveloperAdmin,
  isDeveloperRoute,
  isManagerAdmin,
  isSeoAdmin,
  isSeoRoute,
  isShopAdmin,
} from "../src/lib/admin-roles.ts";

const base = { id: 1, phone: "09120000000", name: null };

const SEO_ADMIN = { ...base, isSeoManager: true };
const STAFF = { ...base, isStaff: true };
const MANAGER = { ...base, isStaff: true, isManagerAdmin: true };
const SUPERUSER = { ...base, isStaff: true, isSuperuser: true };
const CUSTOMER = { ...base };

const SEO_PAGES = [
  "/admin/seo",
  "/admin/seo/pages",
  "/admin/seo/redirects",
  "/admin/seo/settings",
];
const SHOP_PAGES = ["/admin", "/admin/orders", "/admin/users", "/admin/products"];
const DEVELOPER_PAGES = ["/admin/managers", "/admin/seo-admins"];

test("only the SEO manager flag makes a SEO admin", () => {
  assert.equal(isSeoAdmin(SEO_ADMIN), true);
  assert.equal(isSeoAdmin(STAFF), false);
  assert.equal(isSeoAdmin(MANAGER), false);
  assert.equal(isSeoAdmin(SUPERUSER), false);
  assert.equal(isSeoAdmin(CUSTOMER), false);
  assert.equal(isSeoAdmin(null), false);
});

test("manager admin is business-only, never developer", () => {
  assert.equal(isManagerAdmin(MANAGER), true);
  assert.equal(isManagerAdmin(STAFF), false);
  assert.equal(isManagerAdmin(SUPERUSER), false);
  assert.equal(isManagerAdmin(SEO_ADMIN), false);
  assert.equal(isManagerAdmin(CUSTOMER), false);

  assert.equal(isDeveloperAdmin(MANAGER), false);
  assert.equal(isDeveloperAdmin(SUPERUSER), true);
  assert.equal(isDeveloperAdmin(STAFF), false);
  assert.equal(isDeveloperAdmin(SEO_ADMIN), false);
});

test("the business dashboard is open to staff, manager and superuser", () => {
  assert.equal(isShopAdmin(STAFF), true);
  assert.equal(isShopAdmin(MANAGER), true);
  assert.equal(isShopAdmin(SUPERUSER), true);
  assert.equal(isShopAdmin(SEO_ADMIN), false);
  assert.equal(isShopAdmin(CUSTOMER), false);
});

test("route areas are matched on segment boundaries", () => {
  for (const path of SEO_PAGES) assert.equal(isSeoRoute(path), true);
  // مدیریت مدیران سئو ناحیه‌ی سیستمی است، نه ناحیه‌ی سئو
  assert.equal(isSeoRoute("/admin/seo-admins"), false);
  assert.equal(isSeoRoute("/admin/orders"), false);

  for (const path of DEVELOPER_PAGES) assert.equal(isDeveloperRoute(path), true);
  assert.equal(isDeveloperRoute("/admin/managers/12"), true);
  assert.equal(isDeveloperRoute("/admin/orders"), false);
  assert.equal(isDeveloperRoute("/admin/seo"), false);
});

test("manager admin keeps the whole business dashboard", () => {
  for (const path of SHOP_PAGES) {
    assert.equal(adminRedirectFor(MANAGER, path), null);
  }
});

test("manager admin is pushed out of SEO and developer areas", () => {
  for (const path of SEO_PAGES) {
    assert.equal(adminRedirectFor(MANAGER, path), "/admin");
  }
  for (const path of DEVELOPER_PAGES) {
    assert.equal(adminRedirectFor(MANAGER, path), "/admin");
  }
});

test("plain staff is also kept out of the developer area", () => {
  for (const path of DEVELOPER_PAGES) {
    assert.equal(adminRedirectFor(STAFF, path), "/admin");
  }
});

test("only the superuser reaches the developer area", () => {
  for (const path of DEVELOPER_PAGES) {
    assert.equal(adminRedirectFor(SUPERUSER, path), null);
  }
});

test("the existing SEO rule is unchanged", () => {
  // سوپریوزر همچنان به پنل سئو راه ندارد، مدیر سئو دارد
  for (const path of SEO_PAGES) {
    assert.equal(adminRedirectFor(SUPERUSER, path), "/admin");
    assert.equal(adminRedirectFor(STAFF, path), "/admin");
    assert.equal(adminRedirectFor(SEO_ADMIN, path), null);
  }
});

test("SEO admin is pushed out of every non-SEO admin page", () => {
  for (const path of [...SHOP_PAGES, ...DEVELOPER_PAGES]) {
    assert.equal(adminRedirectFor(SEO_ADMIN, path), "/admin/seo");
  }
});

test("anonymous visitors are left to the layout's login screen", () => {
  assert.equal(adminRedirectFor(null, "/admin/seo"), null);
  assert.equal(adminRedirectFor(null, "/admin/managers"), null);
  assert.equal(adminRedirectFor(null, "/admin"), null);
});
