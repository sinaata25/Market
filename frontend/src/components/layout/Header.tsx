import Link from "next/link";
import Image from "next/image";
import CategoryMenu from "./CategoryMenu";
import BrandMenu from "./BrandMenu";
import HeaderActions from "./HeaderActions";

export default function Header() {
  return (
    <header className="sticky top-0 z-40 bg-white shadow-sm">
      {/* نوار بالا */}
      <div className="border-b border-slate-100">
        <div className="site-container grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 py-2.5 lg:flex lg:gap-4 lg:py-3">
          {/* لوگو */}
          <Link href="/" className="flex min-w-0 items-center gap-2 lg:shrink-0">
            <Image
              src="/brand/logo.png"
              alt="گروه صنعتی توانا"
              width={48}
              height={48}
              priority
              className="h-10 w-10 shrink-0 object-contain sm:h-11 sm:w-11"
            />
            <div className="min-w-0 leading-tight">
              <span className="block truncate text-sm font-bold text-brand-700 min-[390px]:text-base sm:text-lg">
                گروه صنعتی توانا
              </span>
              <span className="hidden text-[11px] text-slate-400 min-[390px]:block">
                ابزارآلات کشاورزی
              </span>
            </div>
          </Link>

          {/* جستجو */}
          <div className="relative col-span-2 row-start-2 min-w-0 lg:order-none lg:col-auto lg:row-auto lg:flex-1">
            <input
              aria-label="جستجو در فروشگاه"
              type="text"
              placeholder="جستجو در گروه صنعتی توانا..."
              className="h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-11 pl-4 text-base outline-none transition focus:border-brand-400 focus:bg-white sm:text-sm"
            />
            <span aria-hidden="true" className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
              🔍
            </span>
          </div>

          {/* اکشن‌ها: وضعیت ورود و سبد خرید (کلاینتی، متصل به API) */}
          <HeaderActions />
        </div>
      </div>

      {/* نوار دسته‌بندی */}
      <nav className="border-b border-slate-100 bg-white">
        <div className="site-container">
          <div className="mobile-nav-scroll">
            <div className="flex w-max min-w-full items-center gap-1 py-1 text-sm sm:gap-2 sm:py-1.5 lg:w-full">
              <CategoryMenu />
              <BrandMenu />

              <span className="mx-1 h-5 w-px shrink-0 bg-slate-200" />

              <Link
                href="/incredible"
                className="flex min-h-11 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 font-medium text-accent-700 transition hover:bg-accent-50"
              >
                ⚡ شگفت‌انگیزها
              </Link>
              <Link
                href="/best-sellers"
                className="flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
              >
                پرفروش‌ترین‌ها
              </Link>
              <Link
                href="/blog"
                className="flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
              >
                وبلاگ کشاورزی
              </Link>

              <Link
                href="/support"
                className="mr-auto flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
              >
                سوالی دارید؟
              </Link>
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
}
