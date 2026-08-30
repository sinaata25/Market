// سیاست کش داده‌های فوتر — جدا از لایه‌ی fetch نگه داشته شده تا هم مسیر
// revalidate و هم تست‌ها بدون وابستگی به server-only از آن استفاده کنند.

/**
 * تگ کش فوتر. بک‌اند بعد از هر تغییر مدیر همین تگ را از مسیر
 * /internal/revalidate باطل می‌کند.
 */
export const FOOTER_CACHE_TAG = "footer";

/**
 * سقف کهنگی فوتر وقتی webhook باطل‌سازی تنظیم نشده باشد.
 *
 * عمداً کوتاه است: فوتر داده‌ی کوچکی است و یک درخواست در دقیقه برای هر مسیر
 * هزینه‌ای ندارد، اما پنجره‌ی طولانی یعنی مدیر تغییرش را نمی‌بیند و فکر
 * می‌کند ذخیره نشده است.
 */
export const FOOTER_CACHE_SECONDS = 60;

export type FooterFetchOptions = {
  cache: "force-cache" | "no-store";
  next?: { revalidate: number; tags: string[] };
};

/**
 * گزینه‌های fetch فوتر برای این محیط.
 *
 * در توسعه اصلاً کش نمی‌شود: ویرایش مدیر باید با همان یک بار بارگذاری دیده
 * شود، وگرنه به‌نظر می‌رسد ذخیره کار نکرده است. کش ISR فقط در بیلد و اجرای
 * تولید فعال است، جایی که واقعاً به آن نیاز است.
 */
export function footerFetchOptions(
  nodeEnv: string | undefined
): FooterFetchOptions {
  if (nodeEnv !== "production") return { cache: "no-store" };
  return {
    cache: "force-cache",
    next: { revalidate: FOOTER_CACHE_SECONDS, tags: [FOOTER_CACHE_TAG] },
  };
}
