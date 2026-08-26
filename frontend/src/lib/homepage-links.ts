// مقصد دکمه‌ی «مشاهده همه» هر بخش محصولی — جدا از کامپوننت نگه داشته شده
// تا مستقل تست شود و منطق لینک یک‌جا بماند.

/** بخش‌هایی که صفحه‌ی اختصاصی ثابت دارند */
const FIXED_SECTION_LINKS: Record<string, string> = {
  best_sellers: "/best-sellers",
  incredible_products: "/incredible",
  discounted_products: "/discounts",
};

export type LinkableSection = {
  type: string;
  data: {
    brand?: { slug: string } | null;
    category?: { slug: string } | null;
  };
};

/**
 * آدرس «مشاهده همه» این بخش، یا null اگر بخش مقصدی نداشته باشد.
 *
 * ردیف برند/دسته‌بندی به صفحه‌ی همان برند/دسته‌بندی می‌رود؛ مرجعش از پاسخ
 * API می‌آید، پس تغییر برند در پنل مدیریت لینک را هم به‌روز می‌کند.
 */
export function sectionAllLink(section: LinkableSection): string | null {
  if (section.type === "brand_products") {
    return section.data.brand ? `/brand/${section.data.brand.slug}` : null;
  }
  if (section.type === "category_products") {
    return section.data.category ? `/category/${section.data.category.slug}` : null;
  }
  return FIXED_SECTION_LINKS[section.type] ?? null;
}
