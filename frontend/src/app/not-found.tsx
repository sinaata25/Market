"use client";

import { useEffect } from "react";
import Link from "next/link";

// صفحه ۴۰۴ — بازدید در پنل سئو ثبت می‌شود
export default function NotFound() {
  useEffect(() => {
    fetch("/api/seo/404", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: window.location.pathname,
        referer: document.referrer,
      }),
    }).catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-md px-4 py-20 text-center">
      <span className="mb-4 block text-6xl">🌵</span>
      <h1 className="mb-2 text-xl font-bold text-slate-800">
        صفحه‌ای که دنبالش بودید پیدا نشد
      </h1>
      <p className="mb-6 text-sm leading-7 text-slate-500">
        ممکن است آدرس تغییر کرده یا حذف شده باشد.
      </p>
      <Link
        href="/"
        className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
      >
        بازگشت به صفحه اصلی
      </Link>
    </div>
  );
}
