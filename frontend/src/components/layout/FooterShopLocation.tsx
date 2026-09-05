import FooterIcon from "@/components/layout/FooterIcon";
import type { FooterLocation } from "@/lib/footer";
import { MAP_ASPECT_RATIO, googleMapsEmbedUrl } from "@/lib/footer-map";

/**
 * ردیف موقعیت فروشگاه در فوتر.
 *
 * نقشه یک iframe تنبل است، نه بسته‌ی جاوااسکریپت گوگل: فوتر روی هر صفحه‌ای
 * رندر می‌شود و نباید هزینه‌ی یک SDK نقشه را به همه‌ی صفحه‌ها تحمیل کند.
 * نشانی و دکمه‌ی مسیریابی خارج از iframe هستند، پس اگر نقشه اصلاً بارگذاری
 * نشود (فیلترینگ، افزونه، شبکه) کاربر همچنان نشانی و مسیر را دارد.
 */
export default function FooterShopLocation({
  location,
}: {
  location: FooterLocation;
}) {
  const embedUrl = googleMapsEmbedUrl(
    location,
    process.env.GOOGLE_MAPS_EMBED_API_KEY
  );

  return (
    <section
      aria-labelledby="footer-shop-location"
      className="grid gap-6 border-t border-slate-100 py-8 md:grid-cols-2 md:items-start"
    >
      <div className="min-w-0">
        <h3
          id="footer-shop-location"
          className="font-bold leading-6 text-slate-700"
        >
          موقعیت فروشگاه
        </h3>
        {location.address && (
          <p className="mt-3 flex min-w-0 items-start gap-2 text-sm leading-6 text-slate-500">
            <FooterIcon image={location.icon} className="size-6 p-0.5 text-base" />
            <bdi
              dir="auto"
              className="min-w-0 whitespace-pre-line [overflow-wrap:anywhere]"
            >
              {location.address}
            </bdi>
          </p>
        )}
        <div className="mt-4 flex flex-wrap gap-2">
          <a
            href={location.directionsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            مسیریابی
          </a>
          <a
            href={location.mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-600 transition hover:border-brand-400 hover:text-brand-700"
          >
            مشاهده روی نقشه
          </a>
        </div>
      </div>

      {embedUrl && (
        // قاب با نسبت ثابت رزرو می‌شود تا بارگذاری نقشه چیدمان را نپراند.
        // iframe محتوای تعاملی است و نباید داخل <a> برود؛ اقدام‌های نقشه
        // همان دو دکمه‌ی بالا هستند.
        <div
          style={{ aspectRatio: MAP_ASPECT_RATIO }}
          className="relative w-full overflow-hidden rounded-2xl border border-slate-200 bg-slate-50"
        >
          <iframe
            src={embedUrl}
            title="نقشه‌ی موقعیت فروشگاه"
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="absolute inset-0 h-full w-full border-0"
          />
        </div>
      )}
    </section>
  );
}
