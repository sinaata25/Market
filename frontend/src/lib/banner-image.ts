// انتخاب نسخه‌ی درست تصویر بنر برای اندازه‌ی نمایشگر — بدون وابستگی به
// سرور یا مرورگر، تا هم در کامپوننت سرور و هم در تست قابل استفاده باشد.

/** هم‌مرز با بریک‌پوینت md تیلویند (۴۸rem)؛ از این عرض به بالا دسکتاپ است. */
export const BANNER_DESKTOP_MEDIA = "(min-width: 48rem)";

export type BannerImages = {
  desktopImage: string | null;
  mobileImage: string | null;
};

export type BannerImageSources = {
  /** آدرس <img>؛ وقتی هر دو نسخه هست، نسخه‌ی موبایل (پیش‌فرضِ کوچک‌تر) */
  fallback: string;
  /** فقط وقتی پر است که هر دو نسخه موجود باشند — به <source media> می‌رود */
  desktop: string | null;
  media: string;
};

/**
 * منابع تصویر یک بنر را برمی‌گرداند، یا null اگر هیچ تصویری آپلود نشده باشد.
 *
 * وقتی فقط یک نسخه موجود است، همان در هر عرضی نمایش داده می‌شود و هیچ
 * `<source>`ای ساخته نمی‌شود؛ پس مرورگر هیچ‌وقت هر دو فایل را دانلود نمی‌کند.
 */
export function bannerImageSources(banner: BannerImages): BannerImageSources | null {
  const desktop = banner.desktopImage || null;
  const mobile = banner.mobileImage || null;
  if (!desktop && !mobile) return null;
  return {
    fallback: (mobile ?? desktop) as string,
    desktop: desktop && mobile ? desktop : null,
    media: BANNER_DESKTOP_MEDIA,
  };
}
