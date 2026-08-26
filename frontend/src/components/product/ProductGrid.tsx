/**
 * شبکه‌ی استاندارد کارت محصول.
 *
 * ستون‌ها: ۲ در موبایل، ۳ از sm، ۴ از lg و ۵ از xl. `items-stretch` باعث
 * می‌شود کارت‌های یک ردیف هم‌ارتفاع بمانند (کارت خودش h-full است).
 *
 * حالت `rail`: روی موبایل ردیفِ افقیِ قابل اسکرول و از sm به بالا دقیقاً همان
 * شبکه — تا کارت‌های «اخیراً دیده‌شده» و «شگفت‌انگیزها» با بقیه‌ی سایت یکی باشند.
 */
export default function ProductGrid({
  children,
  rail = false,
  className = "",
}: {
  children: React.ReactNode;
  rail?: boolean;
  className?: string;
}) {
  const columns = rail
    ? "grid w-max grid-flow-col auto-cols-[10.5rem] items-stretch gap-2.5 sm:w-auto sm:grid-flow-row sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5"
    : "grid grid-cols-2 items-stretch gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5";

  return <div className={`${columns} ${className}`}>{children}</div>;
}
