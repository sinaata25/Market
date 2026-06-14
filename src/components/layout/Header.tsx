import Link from "next/link";
import { categories } from "@/lib/products";

export default function Header() {
  return (
    <header className="sticky top-0 z-40 bg-white shadow-sm">
      {/* نوار بالا */}
      <div className="border-b border-slate-100">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          {/* لوگو */}
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-600 text-xl">
              🌾
            </span>
            <div className="leading-tight">
              <span className="block text-lg font-bold text-brand-700">
                ابزار سبز
              </span>
              <span className="block text-[11px] text-slate-400">
                ابزارآلات کشاورزی
              </span>
            </div>
          </Link>

          {/* جستجو */}
          <div className="relative flex-1">
            <input
              type="text"
              placeholder="جستجو در ابزار سبز..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-11 pl-4 text-sm outline-none transition focus:border-brand-400 focus:bg-white"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              🔍
            </span>
          </div>

          {/* اکشن‌ها */}
          <div className="flex shrink-0 items-center gap-2">
            <Link
              href="/login"
              className="hidden items-center gap-2 rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:border-brand-400 hover:text-brand-700 sm:flex"
            >
              <span>👤</span>
              <span>ورود | ثبت‌نام</span>
            </Link>
            <Link
              href="/cart"
              className="relative grid h-11 w-11 place-items-center rounded-xl border border-slate-200 text-xl transition hover:border-brand-400"
            >
              🛒
              <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-brand-600 text-[11px] font-bold text-white font-num">
                ۰
              </span>
            </Link>
          </div>
        </div>
      </div>

      {/* نوار دسته‌بندی */}
      <nav className="border-b border-slate-100 bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2 text-sm">
          <span className="flex items-center gap-1 whitespace-nowrap px-2 font-medium text-slate-500">
            ☰ دسته‌بندی‌ها
          </span>
          {categories.map((c) => (
            <Link
              key={c.slug}
              href={`/category/${c.slug}`}
              className="whitespace-nowrap rounded-lg px-3 py-1.5 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
            >
              {c.emoji} {c.title}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
