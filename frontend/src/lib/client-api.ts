"use client";

// هلپر فراخوانی API جنگو از کلاینت — کوکی‌ها و هدر CSRF را مدیریت می‌کند
// درخواست‌ها به /api/* می‌روند و Next آن‌ها را به جنگو پروکسی می‌کند.

export type ApiResult<T, E = unknown> = {
  ok: boolean;
  data?: T;
  errorData?: E;
  error?: string;
  errorCode?: string;
  status: number;
  retryAfter?: number;
};

export type PdfDownload = {
  blob: Blob;
  filename: string;
};

export const AUTH_CHANGED_EVENT = "auth:changed";
const AUTH_BROADCAST_CHANNEL = "market:auth";
const AUTH_STORAGE_EVENT = "market:auth:changed";

let authChannel: BroadcastChannel | null | undefined;

function getAuthChannel(): BroadcastChannel | null {
  if (authChannel !== undefined) return authChannel;
  if (typeof window === "undefined" || !("BroadcastChannel" in window)) {
    authChannel = null;
    return authChannel;
  }

  try {
    authChannel = new BroadcastChannel(AUTH_BROADCAST_CHANNEL);
  } catch {
    authChannel = null;
  }
  return authChannel;
}

export function notifyAuthChanged() {
  window.dispatchEvent(new CustomEvent(AUTH_CHANGED_EVENT));

  const channel = getAuthChannel();
  if (channel) {
    try {
      channel.postMessage({ changedAt: Date.now() });
      return;
    } catch {
      authChannel = null;
    }
  }

  try {
    localStorage.setItem(
      AUTH_STORAGE_EVENT,
      `${Date.now()}:${Math.random().toString(36).slice(2)}`
    );
  } catch {
    // Same-tab listeners already received the CustomEvent.
  }
}

export function subscribeAuthChanged(listener: () => void): () => void {
  const onLocalChange = () => listener();
  window.addEventListener(AUTH_CHANGED_EVENT, onLocalChange);

  const channel = getAuthChannel();
  const onBroadcast = () => listener();
  const onStorage = (event: StorageEvent) => {
    if (event.key === AUTH_STORAGE_EVENT) listener();
  };

  if (channel) channel.addEventListener("message", onBroadcast);
  else window.addEventListener("storage", onStorage);

  return () => {
    window.removeEventListener(AUTH_CHANGED_EVENT, onLocalChange);
    if (channel) channel.removeEventListener("message", onBroadcast);
    else window.removeEventListener("storage", onStorage);
  };
}

// خواندن کوکی csrftoken که جنگو ست می‌کند
function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

let csrfBootstrap: Promise<void> | null = null;

async function ensureCsrfToken(): Promise<void> {
  if (getCsrfToken()) return;

  if (!csrfBootstrap) {
    csrfBootstrap = fetch("/api/auth/csrf", {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error("CSRF bootstrap failed");
      })
      .finally(() => {
        csrfBootstrap = null;
      });
  }

  await csrfBootstrap;
  if (!getCsrfToken()) throw new Error("CSRF cookie was not set");
}

function getRetryAfter(response: Response): number | undefined {
  const raw = response.headers.get("Retry-After");
  if (!raw) return undefined;
  const seconds = Number.parseInt(raw, 10);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : undefined;
}

function sanitizeFilename(filename: string): string {
  const withoutControlCharacters = Array.from(filename, (character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127 ? "-" : character;
  }).join("");

  return withoutControlCharacters
    .replace(/[\\/:*?"<>|]+/g, "-")
    .trim()
    .replace(/^\.+/, "");
}

export function pdfFilenameFromDisposition(
  contentDisposition: string | null,
  fallbackFilename: string
): string {
  let candidate = "";

  if (contentDisposition) {
    const extendedMatch = /filename\*\s*=\s*([^;]+)/i.exec(
      contentDisposition
    );
    if (extendedMatch) {
      let encoded = extendedMatch[1].trim().replace(/^"|"$/g, "");
      const rfc5987Value = /^[^']*'[^']*'(.*)$/.exec(encoded);
      if (rfc5987Value) encoded = rfc5987Value[1];
      try {
        candidate = decodeURIComponent(encoded);
      } catch {
        candidate = encoded;
      }
    } else {
      const filenameMatch = /filename\s*=\s*(?:"([^"]*)"|([^;]+))/i.exec(
        contentDisposition
      );
      candidate = (filenameMatch?.[1] ?? filenameMatch?.[2] ?? "").trim();
    }
  }

  const fallback = sanitizeFilename(fallbackFilename) || "invoice.pdf";
  const safeFallback = fallback.toLowerCase().endsWith(".pdf")
    ? fallback
    : `${fallback}.pdf`;
  const safeCandidate = sanitizeFilename(candidate);

  return safeCandidate.toLowerCase().endsWith(".pdf")
    ? safeCandidate
    : safeFallback;
}

export async function parsePdfDownloadResponse(
  response: Response,
  fallbackFilename: string
): Promise<ApiResult<PdfDownload>> {
  const contentType = response.headers
    .get("Content-Type")
    ?.split(";", 1)[0]
    .trim()
    .toLowerCase();

  if (!response.ok || contentType !== "application/pdf") {
    const json: unknown = await response.json().catch(() => null);
    const payload =
      json && typeof json === "object"
        ? (json as Record<string, unknown>)
        : null;

    return {
      ok: false,
      error:
        typeof payload?.error === "string"
          ? payload.error
          : response.ok
            ? "پاسخ نامعتبر از سرور"
            : "دریافت فایل با خطا روبه‌رو شد",
      errorData: payload?.data,
      errorCode:
        typeof payload?.errorCode === "string"
          ? payload.errorCode
          : undefined,
      status: response.status,
      retryAfter: getRetryAfter(response),
    };
  }

  const blob = await response.blob();
  if (blob.size === 0) {
    return {
      ok: false,
      error: "فایل دریافت‌شده خالی است",
      status: response.status,
    };
  }

  return {
    ok: true,
    data: {
      blob,
      filename: pdfFilenameFromDisposition(
        response.headers.get("Content-Disposition"),
        fallbackFilename
      ),
    },
    status: response.status,
  };
}

async function downloadPdf(
  path: string,
  fallbackFilename: string
): Promise<ApiResult<PdfDownload>> {
  try {
    const response = await fetch(path, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
    });
    return await parsePdfDownloadResponse(response, fallbackFilename);
  } catch {
    return { ok: false, error: "خطا در ارتباط با سرور", status: 0 };
  }
}

async function request<T, E = unknown>(
  method: string,
  path: string,
  body?: unknown
): Promise<ApiResult<T, E>> {
  try {
    if (method !== "GET") await ensureCsrfToken();
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    // جنگو برای متدهای تغییردهنده، هدر CSRF می‌خواهد
    if (method !== "GET") headers["X-CSRFToken"] = getCsrfToken();

    const res = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: "same-origin",
      cache: "no-store",
    });
    const json = await res.json().catch(() => null);
    if (!json || typeof json !== "object") {
      return {
        ok: false,
        error: "پاسخ نامعتبر از سرور",
        status: res.status,
        retryAfter: getRetryAfter(res),
      };
    }
    const ok = Boolean(json.ok);
    return {
      ok,
      data: ok ? (json.data as T) : undefined,
      errorData: ok ? undefined : (json.data as E | undefined),
      error: json.error as string | undefined,
      errorCode:
        typeof json.errorCode === "string" ? json.errorCode : undefined,
      status: res.status,
      retryAfter: getRetryAfter(res),
    };
  } catch {
    return { ok: false, error: "خطا در ارتباط با سرور", status: 0 };
  }
}

// آپلود فایل (multipart) — Content-Type را مرورگر خودش می‌گذارد
async function upload<T, E = unknown>(
  path: string,
  form: FormData
): Promise<ApiResult<T, E>> {
  try {
    await ensureCsrfToken();
    const res = await fetch(path, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() },
      body: form,
      credentials: "same-origin",
    });
    const json = await res.json().catch(() => null);
    if (!json || typeof json !== "object") {
      return {
        ok: false,
        error: "پاسخ نامعتبر از سرور",
        status: res.status,
        retryAfter: getRetryAfter(res),
      };
    }
    const ok = Boolean(json.ok);
    return {
      ok,
      data: ok ? (json.data as T) : undefined,
      errorData: ok ? undefined : (json.data as E | undefined),
      error: json.error as string | undefined,
      errorCode:
        typeof json.errorCode === "string" ? json.errorCode : undefined,
      status: res.status,
      retryAfter: getRetryAfter(res),
    };
  } catch {
    return { ok: false, error: "خطا در ارتباط با سرور", status: 0 };
  }
}

export const api = {
  get: <T, E = unknown>(path: string) => request<T, E>("GET", path),
  post: <T, E = unknown>(path: string, body?: unknown) =>
    request<T, E>("POST", path, body),
  put: <T, E = unknown>(path: string, body?: unknown) =>
    request<T, E>("PUT", path, body),
  patch: <T, E = unknown>(path: string, body?: unknown) =>
    request<T, E>("PATCH", path, body),
  delete: <T, E = unknown>(path: string, body?: unknown) =>
    request<T, E>("DELETE", path, body),
  downloadPdf,
  upload,
};
