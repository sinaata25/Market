// ساخت آدرس نقشه‌ی جاسازی‌شده‌ی فروشگاه — جدا از کامپوننت نگه داشته شده تا
// مستقل تست شود و تعویض نحوه‌ی نمایش نقشه یک‌جا انجام گیرد.

export type ShopMapLocation = {
  latitude: string;
  longitude: string;
  zoom: number;
};

/** نسبت ابعاد قاب نقشه؛ ثابت بودنش از پرش چیدمان هنگام بارگذاری جلوگیری می‌کند */
export const MAP_ASPECT_RATIO = "16 / 10";

const MIN_ZOOM = 1;
const MAX_ZOOM = 21;

function finiteNumber(value: string, limit: number): number | null {
  // Number("") و Number("  ") هر دو صفرند؛ بدون این بررسی، مختصات خالی
  // سوزن را روی نقطه‌ی صفر اقیانوس اطلس می‌گذارد
  const trimmed = value?.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || Math.abs(parsed) > limit) return null;
  return parsed;
}

/** «lat,lng» یا null اگر مختصات معتبر نباشد */
export function coordinateQuery(location: ShopMapLocation): string | null {
  const latitude = finiteNumber(location.latitude, 90);
  const longitude = finiteNumber(location.longitude, 180);
  if (latitude === null || longitude === null) return null;
  return `${latitude},${longitude}`;
}

function clampedZoom(zoom: number): number {
  if (!Number.isFinite(zoom)) return 15;
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.trunc(zoom)));
}

/**
 * آدرس iframe نقشه، یا null اگر مختصات معتبر نباشد.
 *
 * بدون کلید از مسیر جاسازی ساده‌ی گوگل مپس استفاده می‌شود؛ این مسیر رایگان
 * است و هیچ بسته‌ی جاوااسکریپتی به فروشگاه اضافه نمی‌کند. اگر کلید Maps
 * Embed API تنظیم شده باشد، همان مسیر رسمی و پشتیبانی‌شده به کار می‌رود.
 */
export function googleMapsEmbedUrl(
  location: ShopMapLocation,
  apiKey?: string | null
): string | null {
  const query = coordinateQuery(location);
  if (!query) return null;
  const zoom = clampedZoom(location.zoom);

  if (apiKey) {
    const params = new URLSearchParams({
      key: apiKey,
      q: query,
      zoom: String(zoom),
      language: "fa",
    });
    return `https://www.google.com/maps/embed/v1/place?${params.toString()}`;
  }

  const params = new URLSearchParams({
    q: query,
    z: String(zoom),
    hl: "fa",
    output: "embed",
  });
  return `https://www.google.com/maps?${params.toString()}`;
}

/**
 * موقعیتی که واقعاً باید در فوتر رندر شود، وگرنه null.
 *
 * بک‌اند وقتی مدیر نقشه را خاموش کرده یا مختصاتی ذخیره نشده، اصلاً بلوک
 * موقعیت را نمی‌فرستد؛ این بررسی دوم جلوی رندرشدن مختصات خرابِ احتمالی را
 * می‌گیرد، تا سوزن هرگز روی نقطه‌ی صفر نیفتد.
 */
export function shopLocationToRender<T extends ShopMapLocation>(
  location: T | null | undefined
): T | null {
  if (!location || !coordinateQuery(location)) return null;
  return location;
}
