import Link from "next/link";
import Image from "next/image";
import CategoryMenu from "./CategoryMenu";
import HeaderActions from "./HeaderActions";

export default function Header() {
  return (
    <header className="sticky top-0 z-40 bg-white shadow-sm">
      {/* نوار بالا */}
      <div className="border-b border-slate-100">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          {/* لوگو */}
          <Link href="/" className="flex shrink-0 items-center gap-2">
            <Image
              src="/brand/logo.png"
              alt=""
              width={48}
              height={48}
              priority
              className="h-11 w-11 object-contain"
            />
            <div className="leading-tight">
              <span className="block text-lg font-bold text-brand-700">
                گروه صنعتی توانا
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
              placeholder="جستجو در گروه صنعتی توانا..."
              className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-11 pl-4 text-sm outline-none transition focus:border-brand-400 focus:bg-white"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              🔍
            </span>
          </div>

          {/* اکشن‌ها: وضعیت ورود و سبد خرید (کلاینتی، متصل به API) */}
          <HeaderActions />
        </div>
      </div>

      {/* نوار دسته‌بندی */}
      <nav className="border-b border-slate-100 bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-2 overflow-x-auto px-4 py-1.5 text-sm">
          <CategoryMenu />

          <span className="mx-1 h-5 w-px bg-slate-200" />

          <Link
            href="/incredible"
            className="flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 font-medium text-accent-700 transition hover:bg-accent-50"
          >
            ⚡ شگفت‌انگیزها
          </Link>
          <Link
            href="/best-sellers"
            className="whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
          >
            پرفروش‌ترین‌ها
          </Link>
          <Link
            href="/blog"
            className="whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
          >
            وبلاگ کشاورزی
          </Link>

          <Link
            href="/support"
            className="mr-auto whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
          >
            سوالی دارید؟
          </Link>
        </div>
      </nav>
    </header>
  );
}
