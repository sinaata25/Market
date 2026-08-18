export default function StaticPageUnavailable() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-20 text-center">
      <div className="rounded-3xl border border-slate-100 bg-white px-6 py-14 shadow-sm">
        <span className="text-5xl" aria-hidden="true">
          📄
        </span>
        <h1 className="mt-5 text-lg font-bold text-slate-800">
          نمایش محتوای این صفحه ممکن نشد
        </h1>
        <p className="mt-2 text-sm leading-7 text-slate-500">
          لطفاً چند لحظه دیگر صفحه را دوباره بارگذاری کنید.
        </p>
      </div>
    </div>
  );
}
