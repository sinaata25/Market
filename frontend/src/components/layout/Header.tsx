import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import CategoryMenu from "./CategoryMenu";
import BrandMenu from "./BrandMenu";
import HeaderActions from "./HeaderActions";
import HeaderSearch, { HeaderSearchFallback } from "./HeaderSearch";

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
            <Suspense fallback={<HeaderSearchFallback />}>
              <HeaderSearch />
            </Suspense>
          </div>

          {/* اکشن‌ها: وضعیت ورود و سبد خرید (کلاینتی، متصل به API) */}
          <HeaderActions />
        </div>
      </div>

      {/* نوار دسته‌بندی — در صفحه‌های کوچک فقط دسته‌بندی‌ها و برندها
          نمایش داده می‌شوند؛ بقیه‌ی لینک‌ها از lg به بالا اضافه می‌شوند */}
      <nav className="border-b border-slate-100 bg-white">
        <div className="site-container">
          <div className="flex w-full flex-wrap items-center justify-center gap-x-1 py-1 text-sm sm:gap-x-2 sm:py-1.5 lg:flex-nowrap lg:justify-start">
            <CategoryMenu />
            <BrandMenu />

            <span className="mx-1 hidden h-5 w-px shrink-0 bg-slate-200 lg:block" />

            <Link
              href="/incredible"
              className="hidden min-h-11 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-2 font-medium text-accent-700 transition hover:bg-accent-50 lg:flex"
            >
              ⚡ شگفت‌انگیزها
            </Link>
            <Link
              href="/discounts"
              className="hidden min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700 lg:flex"
            >
              تخفیف‌ها
            </Link>
            <Link
              href="/best-sellers"
              className="hidden min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700 lg:flex"
            >
              پرفروش‌ترین‌ها
            </Link>
            <Link
              href="/blog"
              className="hidden min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700 lg:flex"
            >
              وبلاگ کشاورزی
            </Link>

            <Link
              href="/support"
              className="hidden min-h-11 shrink-0 items-center whitespace-nowrap rounded-lg px-3 py-2 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700 lg:mr-auto lg:flex"
            >
              سوالی دارید؟
            </Link>
          </div>
        </div>
      </nav>
    </header>
  );
}
