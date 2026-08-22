import assert from "node:assert/strict";
import test from "node:test";

import {
  api,
  parsePdfDownloadResponse,
  pdfFilenameFromDisposition,
} from "../src/lib/client-api.ts";

test("PDF response keeps the server-provided invoice filename and body", async () => {
  const response = new Response("%PDF-1.7 invoice", {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": 'attachment; filename="invoice-INV-42.pdf"',
    },
  });

  const result = await parsePdfDownloadResponse(
    response,
    "invoice-fallback.pdf"
  );

  assert.equal(result.ok, true);
  assert.equal(result.status, 200);
  assert.equal(result.data?.filename, "invoice-INV-42.pdf");
  assert.equal(await result.data?.blob.text(), "%PDF-1.7 invoice");
});

test("PDF filename parser supports encoded Unicode filenames", () => {
  assert.equal(
    pdfFilenameFromDisposition(
      "attachment; filename*=UTF-8''%D9%81%D8%A7%DA%A9%D8%AA%D9%88%D8%B1-42.pdf",
      "invoice-42.pdf"
    ),
    "فاکتور-42.pdf"
  );
});

test("unsafe or non-PDF response filenames fall back to a safe PDF name", () => {
  assert.equal(
    pdfFilenameFromDisposition(
      'attachment; filename="../../invoice.html"',
      "invoice-ORDER-7.pdf"
    ),
    "invoice-ORDER-7.pdf"
  );
});

test("JSON API errors are preserved for the invoice UI", async () => {
  const response = Response.json(
    { ok: false, error: "سفارش یافت نشد" },
    { status: 404 }
  );

  const result = await parsePdfDownloadResponse(response, "invoice-42.pdf");

  assert.equal(result.ok, false);
  assert.equal(result.status, 404);
  assert.equal(result.error, "سفارش یافت نشد");
});

test("a successful non-PDF response is rejected", async () => {
  const response = new Response("<html>login</html>", {
    status: 200,
    headers: { "Content-Type": "text/html" },
  });

  const result = await parsePdfDownloadResponse(response, "invoice-42.pdf");

  assert.equal(result.ok, false);
  assert.equal(result.error, "پاسخ نامعتبر از سرور");
});

test("invoice download uses a credentialed, uncached GET request", async () => {
  const originalFetch = globalThis.fetch;
  let request;
  globalThis.fetch = async (input, init) => {
    request = { input, init };
    return new Response("%PDF-1.7", {
      status: 200,
      headers: { "Content-Type": "application/pdf" },
    });
  };

  try {
    const result = await api.downloadPdf(
      "/api/orders/42/invoice",
      "invoice-42.pdf"
    );
    assert.equal(result.ok, true);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(request?.input, "/api/orders/42/invoice");
  assert.equal(request?.init?.method, "GET");
  assert.equal(request?.init?.credentials, "same-origin");
  assert.equal(request?.init?.cache, "no-store");
});
