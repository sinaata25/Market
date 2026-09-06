import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

import { CONTACT_ICONS, contactIconName, contactLinkAttributes, groupContactButtons, isContactButton, isStorefrontPath } from "../src/lib/floating-contacts.ts";
import { FOOTER_CACHE_TAG } from "../src/lib/footer-cache.ts";

// Keep the project's node:test runner; compile the actual TSX without adding a test framework.
const require = createRequire(import.meta.url);
const src = fileURLToPath(new URL("../src/", import.meta.url));
const modules = new Map();
let pathname = "/";
function loadSource(path) {
  const filename = [path, `${path}.ts`, `${path}.tsx`].find(existsSync);
  if (!filename) throw new Error(`Missing source: ${path}`);
  if (modules.has(filename)) return modules.get(filename).exports;
  const compiled = { exports: {} };
  modules.set(filename, compiled);
  const output = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
    fileName: filename,
  }).outputText;
  const localRequire = (name) => {
    if (name === "next/navigation") return { usePathname: () => pathname };
    if (name === "server-only") return {};
    if (name.startsWith("@/")) return loadSource(join(src, name.slice(2)));
    if (name.startsWith(".")) return loadSource(join(dirname(filename), name));
    return require(name);
  };
  new Function("require", "module", "exports", output)(localRequire, compiled, compiled.exports);
  return compiled.exports;
}
const { default: FloatingContacts, ContactButtonStacks } = loadSource(join(src, "components/layout/FloatingContactButtonsClient.tsx"));
const { getFloatingContactButtons } = loadSource(join(src, "lib/floating-contacts-server.ts"));
const button = (overrides = {}) => ({
  id: 1, title: "واتساپ", platform: "whatsapp", url: "https://wa.me/989123456789",
  icon: null, iconName: "whatsapp", tooltipText: "تماس با ما", openInNewTab: true,
  position: "bottom-right", displayOrder: 0, ...overrides,
});
const render = (buttons) => renderToStaticMarkup(createElement(ContactButtonStacks, { buttons }));

test("no configured buttons produces no markup", () => {
  assert.equal(render([]), "");
});

test("one button renders its backend destination, accessible name, tooltip and default icon", () => {
  const html = render([button()]);
  assert.equal((html.match(/<a /g) ?? []).length, 1);
  assert.match(html, /href="https:\/\/wa.me\/989123456789"/);
  assert.match(html, /aria-label="واتساپ"/);
  assert.match(html, /title="تماس با ما"/);
  assert.match(html, /target="_blank"/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.match(html, /<svg aria-hidden="true"/);
  assert.doesNotMatch(html, /tabindex="-1"/);
});

test("multiple buttons sort by order and id within physical left and right stacks", () => {
  const buttons = [button({ id: 3, title: "last", displayOrder: 9 }), button({ id: 2, title: "left", position: "bottom-left" }), button({ id: 1, title: "first" })];
  const grouped = groupContactButtons(buttons);
  assert.deepEqual(grouped["bottom-right"].map((item) => item.id), [1, 3]);
  assert.deepEqual(grouped["bottom-left"].map((item) => item.id), [2]);
  assert.deepEqual(buttons.map((item) => item.id), [3, 2, 1], "does not mutate incoming configuration");
  const html = render(buttons);
  assert.equal((html.match(/<a /g) ?? []).length, 3);
  assert.match(html, /data-floating-contacts="bottom-left"/);
  assert.match(html, /data-floating-contacts="bottom-right"/);
  assert.ok(html.indexOf('aria-label="first"') < html.indexOf('aria-label="last"'));
  assert.deepEqual(groupContactButtons([button({ id: 2 }), button({ id: 1 })])["bottom-right"].map((item) => item.id), [1, 2]);
});

test("a custom uploaded or selected image takes precedence over the built-in icon", () => {
  const html = render([button({ icon: "/media/contacts/icons/my-icon.webp" })]);
  assert.match(html, /<img src="\/media\/contacts\/icons\/my-icon.webp"/);
  assert.match(html, /alt="" aria-hidden="true"/);
  assert.doesNotMatch(html, /<svg/);
});

test("all default icons and arbitrary future platform fallbacks remain visible", () => {
  for (const name of Object.keys(CONTACT_ICONS)) {
    const html = render([button({ platform: name, iconName: "" })]);
    assert.match(html, /aria-hidden="true"/);
  }
  assert.equal(contactIconName(button({ platform: "future", iconName: "" })), "custom");
  assert.equal(contactIconName(button({ platform: "telegram", iconName: "phone" })), "phone");
  assert.match(render([button({ platform: "future", iconName: "" })]), /<svg/);
});

test("phone, SMS and email use their backend links without opening empty tabs", () => {
  for (const url of ["tel:+989123456789", "sms:09123456789", "mailto:hello@example.com"]) {
    const html = render([button({ url })]);
    assert.ok(html.includes(`href="${url}"`));
    assert.doesNotMatch(html, /target=/);
  }
  assert.equal(contactLinkAttributes(button({ openInNewTab: false })).target, undefined);
});

test("unsafe destinations and unknown positions cannot produce a floating link", () => {
  for (const url of ["javascript:alert(1)", "data:text/html,test", "//example.com"]) {
    assert.equal(render([button({ url })]), "");
  }
  assert.equal(render([button({ position: "unknown" })]), "");
});

test("admin routes never render buttons, including after a client navigation", () => {
  for (pathname of ["/admin", "/admin/footer", "/admin/floating-contact-buttons", "/admin/seo"]) {
    assert.equal(isStorefrontPath(pathname), false);
    assert.equal(renderToStaticMarkup(createElement(FloatingContacts, { buttons: [button()] })), "");
  }
  for (pathname of ["/", "/product/1", "/cart", "/profile", "/administrator"]) {
    assert.equal(isStorefrontPath(pathname), true);
    assert.match(renderToStaticMarkup(createElement(FloatingContacts, { buttons: [button()] })), /data-floating-contacts/);
  }
  pathname = "/";
});

test("untrusted text is escaped and an empty tooltip omits title", () => {
  const html = render([button({ title: '<img src=x onerror="alert(1)">', tooltipText: "" })]);
  assert.doesNotMatch(html, /<img src=x/);
  assert.match(html, /&lt;img/);
  assert.doesNotMatch(html, / title=/);
});

test("configuration fetching shares icon revalidation and caches only in production", async (t) => {
  const previous = process.env.NODE_ENV;
  t.after(() => { if (previous === undefined) delete process.env.NODE_ENV; else process.env.NODE_ENV = previous; });
  const fetch = t.mock.method(globalThis, "fetch", async () => Response.json({ ok: true, data: { buttons: [button()] } }));
  process.env.NODE_ENV = "production";
  assert.equal((await getFloatingContactButtons()).length, 1);
  const [url, options] = fetch.mock.calls[0].arguments;
  assert.ok(url.endsWith("/api/site-settings/floating-contact-buttons"));
  assert.equal(options.cache, "force-cache");
  assert.deepEqual(options.next.tags, [FOOTER_CACHE_TAG]);
  assert.ok(options.next.revalidate <= 60);
  process.env.NODE_ENV = "development";
  await getFloatingContactButtons();
  assert.equal(fetch.mock.calls[1].arguments[1].cache, "no-store");
});

test("failed or malformed backend configuration does not break the storefront", async (t) => {
  const fetch = t.mock.method(globalThis, "fetch");
  for (const json of [null, { ok: false }, { ok: true, data: {} }, { ok: true, data: { buttons: [null, {}, button({ position: "top" })] } }]) {
    fetch.mock.mockImplementation(async () => Response.json(json));
    assert.deepEqual(await getFloatingContactButtons(), []);
  }
  fetch.mock.mockImplementation(async () => { throw new Error("unavailable"); });
  assert.deepEqual(await getFloatingContactButtons(), []);
  assert.equal(isContactButton(button()), true);
  assert.equal(isContactButton(button({ displayOrder: -1 })), false);
});

test("mobile CSS keeps touch targets, physical RTL corners, safe areas and comparison clearance", () => {
  const css = readFileSync(join(src, "app/globals.css"), "utf8");
  const stack = css.slice(css.indexOf(".floating-contact-stack {"), css.indexOf("body:has([data-compare-tray])"));
  assert.match(stack, /position: fixed/);
  assert.match(stack, /flex-direction: column/);
  assert.match(stack, /env\(safe-area-inset-bottom/);
  assert.match(stack, /env\(safe-area-inset-left/);
  assert.match(stack, /env\(safe-area-inset-right/);
  assert.match(stack, /var\(--compare-tray-h, 0px\)/);
  assert.match(stack, /max-height:/);
  assert.match(stack, /overflow-y: auto/);
  assert.match(stack, /width: 3rem/);
  assert.match(stack, /height: 3rem/);
  assert.match(stack, /:focus-visible/);
  assert.match(stack, /prefers-reduced-motion/);
});
