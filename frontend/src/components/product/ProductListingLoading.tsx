export default function ProductListingLoading() {
  return (
    <div className="site-shell py-6" role="status" aria-live="polite">
      <div className="mb-6 h-28 animate-pulse rounded-3xl bg-slate-100" />
      <div className="mb-5 h-14 animate-pulse rounded-2xl bg-slate-100" />
      <span className="sr-only">در حال دریافت نتایج جستجو...</span>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }, (_, index) => (
          <div
            key={index}
            className="h-72 animate-pulse rounded-2xl bg-slate-100"
          />
        ))}
      </div>
    </div>
  );
}
