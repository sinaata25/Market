import { footerIconSource } from "@/lib/footer-layout";

/**
 * آیکن فوتر — فایل تصویری انتخاب‌شده در داشبورد، و اگر انتخاب نشده باشد
 * ایموجی جایگزین.
 *
 * آیکن‌ها تزیینی‌اند و متن کنارشان معنا را می‌رساند، پس عمداً alt خالی
 * دارند و از دید صفحه‌خوان پنهان می‌شوند.
 */
export default function FooterIcon({
  image,
  emoji,
  className,
}: {
  image: string | null;
  emoji?: string | null;
  className: string;
}) {
  const source = footerIconSource(image, emoji);

  if (source.kind === "image") {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={source.value}
        alt=""
        aria-hidden="true"
        loading="lazy"
        className={`${className} shrink-0 object-contain`}
      />
    );
  }
  if (source.kind === "emoji") {
    return (
      <span aria-hidden="true" className="shrink-0">
        {source.value}
      </span>
    );
  }
  return null;
}
