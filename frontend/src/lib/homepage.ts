import "server-only";
import type { Brand as BrandDTO, Category as CategoryDTO, Product as ProductDTO } from "@/lib/products";

// لایه‌ی خواندن بخش‌های صفحه اصلی سمت سرور Next — از API جنگو fetch می‌کند
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store" });
  const json = await res.json();
  if (!json.ok) throw new Error(json.error ?? `خطای API: ${path}`);
  return json.data as T;
}

export type HomepageSectionType =
  | "banner"
  | "categories"
  | "brands"
  | "best_sellers"
  | "incredible_products"
  | "discounted_products"
  | "new_products"
  | "all_products"
  | "product_collection"
  | "brand_products"
  | "category_products"
  | "recently_viewed";

export type HomepageBanner = {
  id: number;
  title: string | null;
  subtitle: string | null;
  // دو نسخه‌ی مستقل؛ فروشگاه بسته به عرض نمایشگر یکی را نمایش می‌دهد
  desktopImage: string | null;
  mobileImage: string | null;
  theme: "brand" | "secondary" | "accent";
  linkUrl: string | null;
  linkLabel: string | null;
};

export type HomepageSection = {
  id: number;
  // نوع می‌تواند در آینده مقادیر جدیدی داشته باشد که فرانت هنوز آن‌ها را نمی‌شناسد
  type: HomepageSectionType | (string & {});
  position: number;
  title: string | null;
  limit: number;
  data: {
    banner?: HomepageBanner;
    categories?: CategoryDTO[];
    brands?: BrandDTO[];
    products?: ProductDTO[];
    // ردیف برند/دسته‌بندی: مرجع بخش، برای لینک «مشاهده همه»
    brand?: BrandDTO;
    category?: { slug: string; title: string };
    // فقط بخش «همه محصولات»: تعداد کل کاتالوگ برای ساخت صفحه‌بندی
    total?: number;
  };
};

export async function getHomepageSections(): Promise<HomepageSection[]> {
  const data = await apiGet<{ sections: HomepageSection[] }>("/api/home/sections");
  return data.sections;
}
