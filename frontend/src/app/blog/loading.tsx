export default function BlogLoading() {
  return (
    <div className="mx-auto max-w-7xl animate-pulse px-4 py-8" aria-label="در حال بارگذاری وبلاگ">
      <div className="mb-7 h-52 rounded-3xl bg-slate-200" />
      <div className="mb-6 h-28 rounded-2xl bg-white" />
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="overflow-hidden rounded-2xl bg-white">
            <div className="aspect-[16/9] bg-slate-200" />
            <div className="space-y-3 p-5"><div className="h-4 w-2/3 rounded bg-slate-200" /><div className="h-3 rounded bg-slate-100" /><div className="h-3 w-4/5 rounded bg-slate-100" /></div>
          </div>
        ))}
      </div>
    </div>
  );
}
