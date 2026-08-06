"use client";

export default function BlogError({ reset }: { reset: () => void }) {
  return (
    <div className="mx-auto max-w-md px-4 py-20 text-center">
      <span className="text-6xl" aria-hidden>🌧️</span>
      <h1 className="mt-4 text-lg font-bold text-slate-800">نمایش وبلاگ با خطا روبه‌رو شد</h1>
      <p className="mt-2 text-sm leading-7 text-slate-500">اتصال به سرور را بررسی کنید و دوباره تلاش کنید.</p>
      <button onClick={reset} className="mt-5 rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white">تلاش دوباره</button>
    </div>
  );
}
