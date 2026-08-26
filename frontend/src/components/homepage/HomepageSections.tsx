import Link from "next/link";
import ProductCard from "@/components/product/ProductCard";
import ProductGrid from "@/components/product/ProductGrid";
import ProductRail from "@/components/product/ProductRail";
import type {
  HomepageBanner,
  HomepageSection,
  HomepageSectionType,
} from "@/lib/homepage";
import { bannerImageSources } from "@/lib/banner-image";
import RecentlyViewedSection from "@/components/homepage/RecentlyViewedSection";
import AllProductsSection from "@/components/homepage/AllProductsSection";

const BANNER_THEMES: Record<HomepageBanner["theme"], string> = {
  brand: "from-secondary-700 to-brand-600",
  secondary: "from-secondary-900 to-secondary-600",
  accent: "from-accent-600 to-accent-400",
};

function BannerSection({
  banner,
  title,
}: {
  banner: HomepageBanner;
  title?: string | null;
}) {
  const visibleTitle = title ?? banner.title;
  const images = bannerImageSources(banner);
  return (
    <section
      className={`relative overflow-hidden rounded-3xl bg-gradient-to-l ${BANNER_THEMES[banner.theme]} px-6 py-12 text-white sm:px-12 sm:py-16`}
    >
      {images && (
        // مرورگر فقط نسخه‌ی متناسب با عرض نمایشگر را دانلود می‌کند
        <picture className="pointer-events-none absolute inset-0">
          {images.desktop && (
            <source media={images.media} srcSet={images.desktop} />
          )}
          <img
            src={images.fallback}
            alt=""
            className="h-full w-full object-cover opacity-30"
          />
        </picture>
      )}
      <div className="relative z-10 max-w-lg">
        {visibleTitle && (
          <h2 className="mb-3 text-2xl font-bold leading-relaxed sm:text-3xl">
            {visibleTitle}
          </h2>
        )}
        {banner.subtitle && (
          <p className="mb-6 text-sm leading-7 text-white/90 sm:text-base">
            {banner.subtitle}
          </p>
        )}
        {banner.linkUrl && banner.linkLabel && (
          <Link
            href={banner.linkUrl}
            className="inline-block rounded-xl bg-white px-6 py-3 text-sm font-bold text-brand-700 transition hover:bg-brand-50"
          >
            {banner.linkLabel}
          </Link>
        )}
      </div>
      {!images && (
        <span className="pointer-events-none absolute -left-6 bottom-0 text-[10rem] opacity-20 sm:opacity-30">
          🚜
        </span>
      )}
    </section>
  );
}

function CategoriesSection({ section }: { section: HomepageSection }) {
  const categories = section.data.categories ?? [];
  if (!categories.length) return null;
  return (
    <section>
      {section.title && (
        <h2 className="mb-4 text-lg font-bold text-slate-800">{section.title}</h2>
      )}
      <div className="grid grid-cols-2 gap-3 min-[420px]:grid-cols-4 sm:grid-cols-8">
        {categories.map((category) => (
          <Link
            key={category.slug}
            href={`/category/${category.slug}`}
            className="flex min-w-0 flex-col items-center justify-center gap-2 rounded-2xl border border-slate-100 bg-white p-4 transition hover:border-brand-200 hover:shadow-sm"
          >
            {category.icon && (
              <span className="grid h-14 w-14 place-items-center rounded-full bg-brand-50">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={category.icon} alt="" className="h-9 w-9 object-contain" />
              </span>
            )}
            <span className="max-w-full truncate text-center text-xs text-slate-600">
              {category.title}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function BrandsSection({ section }: { section: HomepageSection }) {
  const brands = section.data.brands ?? [];
  if (!brands.length) return null;
  return (
    <section>
      {section.title && (
        <h2 className="mb-4 text-lg font-bold text-slate-800">{section.title}</h2>
      )}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        {brands.map((brand) => (
          <Link
            key={brand.slug}
            href={`/brand/${brand.slug}`}
            className="flex min-w-0 items-center justify-center gap-3 rounded-2xl border border-slate-100 bg-white p-4 transition hover:border-brand-200 hover:shadow-sm"
          >
            {brand.logo ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={brand.logo} alt="" className="h-10 w-10 object-contain" />
            ) : (
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-50 text-sm font-bold text-brand-700">
                {brand.name.slice(0, 1)}
              </span>
            )}
            <span className="truncate text-sm font-medium text-slate-700">
              {brand.name}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}

const PRODUCT_LINKS: Partial<Record<HomepageSectionType, string>> = {
  best_sellers: "/best-sellers",
  incredible_products: "/incredible",
  discounted_products: "/discounts",
};

function ProductSection({ section }: { section: HomepageSection }) {
  const products = section.data.products ?? [];
  if (!products.length) return null;
  const isDeals =
    section.type === "discounted_products" ||
    section.type === "incredible_products";
  const allLink = PRODUCT_LINKS[section.type as HomepageSectionType];

  return (
    <section
      className={
        isDeals
          ? "overflow-hidden rounded-3xl bg-gradient-to-l from-accent-600 to-accent-400 p-3 sm:p-5"
          : ""
      }
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        {section.title && (
          <h2
            className={`text-lg font-bold ${isDeals ? "text-secondary-900" : "text-slate-800"}`}
          >
            {isDeals ? "⚡ " : section.type === "best_sellers" ? "🔥 " : ""}
            {section.title}
          </h2>
        )}
        {allLink && (
          <Link
            href={allLink}
            className={
              isDeals
                ? "shrink-0 rounded-xl bg-secondary-900/10 px-4 py-2 text-xs font-medium text-secondary-900 transition hover:bg-secondary-900/20"
                : "shrink-0 text-sm text-brand-600 transition hover:text-brand-700"
            }
          >
            مشاهده همه ←
          </Link>
        )}
      </div>
      {isDeals ? (
        <ProductRail>
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ProductRail>
      ) : (
        <ProductGrid>
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ProductGrid>
      )}
    </section>
  );
}

/**
 * بخش «همه محصولات» — برخلاف بقیه‌ی بخش‌های محصولی، کل کاتالوگ را
 * صفحه‌به‌صفحه نشان می‌دهد؛ پس علاوه بر محصولاتِ صفحه‌ی اول، تعداد کل را هم
 * از API می‌گیرد تا صفحه‌بندی همان‌جا ساخته شود. `limit` این بخش یعنی تعداد
 * کالای هر صفحه.
 */
function AllProductsHomeSection({ section }: { section: HomepageSection }) {
  const products = section.data.products ?? [];
  const total = section.data.total ?? products.length;
  const perPage = section.limit || products.length || 1;

  if (!products.length) return null;

  return (
    <AllProductsSection
      title={section.title ?? undefined}
      perPage={perPage}
      initial={{
        items: products,
        total,
        pages: Math.ceil(total / perPage),
      }}
    />
  );
}

const SECTION_RENDERERS: Partial<
  Record<HomepageSectionType, (section: HomepageSection) => React.ReactNode>
> = {
  banner: (section) =>
    section.data.banner ? (
      <BannerSection banner={section.data.banner} title={section.title} />
    ) : null,
  categories: (section) => <CategoriesSection section={section} />,
  brands: (section) => <BrandsSection section={section} />,
  best_sellers: (section) => <ProductSection section={section} />,
  incredible_products: (section) => <ProductSection section={section} />,
  discounted_products: (section) => <ProductSection section={section} />,
  new_products: (section) => <ProductSection section={section} />,
  all_products: (section) => <AllProductsHomeSection section={section} />,
  product_collection: (section) => <ProductSection section={section} />,
  recently_viewed: (section) => (
    <RecentlyViewedSection
      title={section.title ?? "محصولات اخیراً مشاهده‌شده"}
      limit={section.limit}
    />
  ),
};

export function HomepageSections({ sections }: { sections: HomepageSection[] }) {
  return (
    <div className="space-y-10">
      {sections.map((section) => {
        const renderer = SECTION_RENDERERS[section.type as HomepageSectionType];
        return renderer ? (
          <div key={section.id} className="empty:hidden">
            {renderer(section)}
          </div>
        ) : null;
      })}
    </div>
  );
}
