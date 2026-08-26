import ProductGrid from "@/components/product/ProductGrid";

/**
 * ردیف محصولات: روی موبایل اسکرول افقی، از sm به بالا شبکه‌ی استاندارد.
 *
 * پدینگ عمودی و `-mx-1/px-1` عمدی‌اند: ظرفِ `overflow-x-auto` محورِ عمودی را
 * هم به auto تبدیل می‌کند و بدون این فاصله، بالاآمدن کارت هنگام هاور، سایه و
 * حلقه‌ی فوکوس بریده می‌شوند.
 */
export default function ProductRail({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="-mx-1 max-w-full overflow-x-auto overscroll-x-contain px-1 py-1 sm:mx-0 sm:overflow-visible sm:px-0 sm:py-0">
      <ProductGrid rail>{children}</ProductGrid>
    </div>
  );
}
