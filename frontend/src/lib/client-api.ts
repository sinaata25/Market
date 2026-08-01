"use client";

// هلپر فراخوانی API جنگو از کلاینت — کوکی‌ها و هدر CSRF را مدیریت می‌کند
// درخواست‌ها به /api/* می‌روند و Next آن‌ها را به جنگو پروکسی می‌کند.

export type ApiResult<T> = {
  ok: boolean;
  data?: T;
  error?: string;
  status: number;
};

// خواندن کوکی csrftoken که جنگو ست می‌کند
function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<ApiResult<T>> {
  try {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    // جنگو برای متدهای تغییردهنده، هدر CSRF می‌خواهد
    if (method !== "GET") headers["X-CSRFToken"] = getCsrfToken();

    const res = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const json = await res.json().catch(() => null);
    if (!json || typeof json !== "object") {
      return {
        ok: false,
        error: "پاسخ نامعتبر از سرور",
        status: res.status,
      };
    }
    return {
      ok: Boolean(json.ok),
      data: json.data as T,
      error: json.error as string | undefined,
      status: res.status,
    };
  } catch {
    return { ok: false, error: "خطا در ارتباط با سرور", status: 0 };
  }
}

// آپلود فایل (multipart) — Content-Type را مرورگر خودش می‌گذارد
async function upload<T>(path: string, form: FormData): Promise<ApiResult<T>> {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "X-CSRFToken": getCsrfToken() },
      body: form,
    });
    const json = await res.json().catch(() => null);
    if (!json || typeof json !== "object") {
      return {
        ok: false,
        error: "پاسخ نامعتبر از سرور",
        status: res.status,
      };
    }
    return {
      ok: Boolean(json.ok),
      data: json.data as T,
      error: json.error as string | undefined,
      status: res.status,
    };
  } catch {
    return { ok: false, error: "خطا در ارتباط با سرور", status: 0 };
  }
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string, body?: unknown) =>
    request<T>("DELETE", path, body),
  upload,
};
