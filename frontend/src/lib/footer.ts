import "server-only";

// لایه‌ی خواندن فوتر سمت سرور Next — کل فوتر در یک درخواست از جنگو می‌آید
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/**
 * فوتر روی تقریباً همه‌ی صفحه‌هاست، پس پاسخ آن کش می‌شود. بک‌اند بعد از هر
 * تغییر مدیر همین تگ را از مسیر /internal/revalidate باطل می‌کند؛ انقضای
 * زمانی هم به‌عنوان تور ایمنی باقی می‌ماند.
 */
export const FOOTER_CACHE_TAG = "footer";
const FOOTER_CACHE_SECONDS = 300;

export type FooterItemType =
  | "link"
  | "text"
  | "image"
  | "phone"
  | "email"
  | "address"
  | "social";

export type FooterItem = {
  id: number;
  // نوع می‌تواند در آینده مقادیر تازه‌ای بگیرد که فرانت هنوز نمی‌شناسد
  type: FooterItemType | (string & {});
  label: string | null;
  text: string | null;
  url: string | null;
  image: string | null;
  icon: string | null;
  openInNewTab: boolean;
  isExternal: boolean;
  position: number;
};

export type FooterSectionVariant = "column" | "strip";

export type FooterSection = {
  id: number;
  title: string | null;
  variant: FooterSectionVariant | (string & {});
  description: string | null;
  position: number;
  items: FooterItem[];
};

export type FooterLocation = {
  address: string | null;
  latitude: string;
  longitude: string;
  zoom: number;
  /** «مشاهده روی نقشه» — پیوند دلخواه مدیر یا ساخته‌شده از مختصات */
  mapsUrl: string;
  /** «مسیریابی» — همیشه از مختصات ذخیره‌شده ساخته می‌شود */
  directionsUrl: string;
};

export type FooterSettings = {
  brandTitle: string | null;
  logo: string | null;
  description: string | null;
  copyright: string | null;
  address: string | null;
  phone: string | null;
  phoneUrl: string | null;
  email: string | null;
  emailUrl: string | null;
  /** null یعنی مدیر نقشه را خاموش کرده یا مختصاتی ذخیره نشده است */
  location: FooterLocation | null;
};

export type FooterData = {
  settings: FooterSettings;
  sections: FooterSection[];
};

function isFooterData(value: unknown): value is FooterData {
  if (!value || typeof value !== "object") return false;
  const data = value as Partial<FooterData>;
  return (
    !!data.settings &&
    typeof data.settings === "object" &&
    Array.isArray(data.sections)
  );
}

/** کل فوتر، یا null اگر بک‌اند در دسترس نباشد — فوتر نباید صفحه را بشکند */
export async function getFooter(): Promise<FooterData | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/footer`, {
      cache: "force-cache",
      next: { revalidate: FOOTER_CACHE_SECONDS, tags: [FOOTER_CACHE_TAG] },
    });
    const json = await response.json().catch(() => null);
    if (!response.ok || !json?.ok || !isFooterData(json.data)) return null;
    return json.data;
  } catch {
    return null;
  }
}
