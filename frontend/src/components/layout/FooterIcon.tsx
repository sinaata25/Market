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

  if (source.kind === "none") return null;

  const slotClassName = `${className} inline-flex shrink-0 items-center justify-center overflow-hidden leading-none`;

  if (source.kind === "image") {
    return (
      <span aria-hidden="true" className={slotClassName}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={source.value}
          alt=""
          loading="lazy"
          className="h-full w-full object-contain"
        />
      </span>
    );
  }

  return (
    <span aria-hidden="true" className={slotClassName}>
      {source.value}
    </span>
  );
}
