// منطق چیدمان فوتر — جدا از کامپوننت نگه داشته شده تا مستقل تست شود و
// افزودن نوع تازه‌ی محتوا یا بخش، رندر را غافلگیر نکند.

export type FooterLinkSource = {
  url: string | null;
  isExternal: boolean;
  openInNewTab: boolean;
};

export type FooterLinkAttributes = {
  href: string;
  /** بیرونی‌ها با <a> ساده رندر می‌شوند، نه با <Link> پیمایش کلاینتی */
  external: boolean;
  target?: "_blank";
  rel?: string;
};

/**
 * تعداد ستون‌های فوتر متغیر است: ستون معرفی برند به‌علاوه‌ی بخش‌های ستونیِ
 * مدیر. کلاس‌ها عمداً به‌صورت رشته‌ی کامل نوشته شده‌اند تا Tailwind بتواند
 * آن‌ها را در سورس ببیند.
 */
const COLUMN_GRID_CLASSES: Record<number, string> = {
  0: "lg:grid-cols-1",
  1: "lg:grid-cols-2",
  2: "lg:grid-cols-3",
};

// چهار ستون، حداقل عرض عملیِ ستون‌ها را در لپ‌تاپ و دسکتاپ حفظ می‌کند؛
// بخش‌های بیشتر به ردیف بعد می‌روند و دیگر در تبلت به ۵ یا ۶ ستون فشرده
// نمی‌شوند.
const WIDEST_COLUMN_GRID = "lg:grid-cols-4";

/** کلاس شبکه‌ی ستون‌های فوتر برای این تعداد بخش ستونی */
export function footerColumnGridClass(columnSectionCount: number): string {
  if (columnSectionCount < 0) return COLUMN_GRID_CLASSES[0];
  return COLUMN_GRID_CLASSES[columnSectionCount] ?? WIDEST_COLUMN_GRID;
}

/**
 * ویژگی‌های پیوند یک آیتم فوتر، یا null اگر مقصدی نداشته باشد.
 *
 * `rel` فقط وقتی افزوده می‌شود که پیوند بیرونی در تب تازه باز شود — همان
 * جایی که `window.opener` خطر دارد.
 */
export function footerLinkAttributes(
  item: FooterLinkSource
): FooterLinkAttributes | null {
  const href = item.url?.trim();
  if (!href) return null;

  const newTab = item.openInNewTab;
  return {
    href,
    external: item.isExternal,
    ...(newTab ? { target: "_blank" as const } : {}),
    ...(newTab && item.isExternal ? { rel: "noopener noreferrer" } : {}),
  };
}

export type PartitionedSection = { variant: string };

/**
 * بخش‌های نوار مزیت (بالای فوتر) از بخش‌های ستونی جدا می‌شوند؛ ترتیب مدیر
 * درون هر گروه حفظ می‌شود.
 */
export function partitionFooterSections<T extends PartitionedSection>(
  sections: readonly T[]
): { strips: T[]; columns: T[]; badges: T[] } {
  return {
    strips: sections.filter((section) => section.variant === "strip"),
    // نوع ناشناخته همچنان ستون می‌شود؛ نمادها ناحیه‌ی مخصوص خود را دارند.
    columns: sections.filter((section) => section.variant !== "strip" && section.variant !== "badges"),
    badges: sections.filter((section) => section.variant === "badges"),
  };
}

export type FooterIconSource =
  | { kind: "image"; value: string }
  | { kind: "emoji"; value: string }
  | { kind: "none" };

/**
 * چه چیزی به‌جای آیکن رندر شود.
 *
 * فایل آیکنِ انتخاب‌شده در داشبورد همیشه مقدم است؛ ایموجی فقط میراث
 * پیکربندی‌های قدیمی و راه سریع مدیر است، نه حالت پیش‌فرض.
 */
export function footerIconSource(
  image: string | null | undefined,
  emoji?: string | null
): FooterIconSource {
  const file = image?.trim();
  if (file) return { kind: "image", value: file };
  const fallback = emoji?.trim();
  if (fallback) return { kind: "emoji", value: fallback };
  return { kind: "none" };
}
