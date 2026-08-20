import "server-only";
import { cache } from "react";
import type {
  Brand as BrandDTO,
  Product as ProductDTO,
  ProductSpecification,
  Category as CategoryDTO,
} from "@/lib/products";

// لایه‌ی خواندن کاتالوگ سمت سرور Next — از API جنگو fetch می‌کند
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store" });
  const json = await res.json();
  if (!json.ok) throw new Error(json.error ?? `خطای API: ${path}`);
  return json.data as T;
}

export async function getCategories(): Promise<CategoryDTO[]> {
  const data = await apiGet<{ categories: CategoryDTO[] }>("/api/categories");
  return data.categories;
}

export async function getBrands(): Promise<BrandDTO[]> {
  const data = await apiGet<{ brands: BrandDTO[] }>("/api/brands");
  return data.brands;
}

export type ProductListParams = {
  categorySlug?: string;
  brandSlug?: string;
  search?: string;
  sort?: "newest" | "cheapest" | "expensive" | "popular" | "featured";
  page?: number;
  perPage?: number;
  onlyDiscounted?: boolean;
  // فقط محصولاتی که مدیر برای بخش «پرفروش‌ترین‌ها» انتخاب کرده — نه آمار فروش واقعی
  bestSeller?: boolean;
};

export type ProductListResult = {
  items: ProductDTO[];
  total: number;
  page: number;
  perPage: number;
  pages: number;
};

export type ProductDetail = ProductDTO & {
  specifications: ProductSpecification[];
};

export type ProductDetailResult = {
  product: ProductDetail;
  related: ProductDTO[];
};

export async function getProducts(
  params: ProductListParams = {}
): Promise<ProductListResult> {
  const qs = new URLSearchParams();
  if (params.categorySlug) qs.set("category", params.categorySlug);
  if (params.brandSlug) qs.set("brand", params.brandSlug);
  if (params.search) qs.set("search", params.search);
  if (params.sort) qs.set("sort", params.sort);
  if (params.page) qs.set("page", String(params.page));
  if (params.perPage) qs.set("perPage", String(params.perPage));
  if (params.onlyDiscounted) qs.set("discounted", "true");
  if (params.bestSeller) qs.set("bestSeller", "true");
  const query = qs.toString();
  return apiGet<ProductListResult>(`/api/products${query ? `?${query}` : ""}`);
}

export const getProductDetailById = cache(async function getProductDetailById(
  id: number
): Promise<ProductDetailResult | null> {
  try {
    return await apiGet<ProductDetailResult>(`/api/products/${id}`);
  } catch {
    return null;
  }
});

// یافتن محصول با نامک سئو (تنظیم‌شده در پنل سئو)
export const getProductBySlug = cache(async function getProductBySlug(
  slug: string
): Promise<ProductDetailResult | null> {
  try {
    return await apiGet<ProductDetailResult>(
      `/api/products/slug/${encodeURIComponent(slug)}`
    );
  } catch {
    return null;
  }
});
