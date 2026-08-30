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
  0: "md:grid-cols-1",
  1: "md:grid-cols-2",
  2: "md:grid-cols-3",
  3: "md:grid-cols-4",
  4: "md:grid-cols-5",
  5: "md:grid-cols-6",
};

const WIDEST_COLUMN_GRID = COLUMN_GRID_CLASSES[5];

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
): { strips: T[]; columns: T[] } {
  return {
    strips: sections.filter((section) => section.variant === "strip"),
    // هر چیزی که نوار نیست ستون است، تا نوع تازه‌ی بخش بی‌صدا ناپدید نشود
    columns: sections.filter((section) => section.variant !== "strip"),
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
