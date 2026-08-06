import "server-only";
import { cache } from "react";
import type {
  BlogCategory,
  BlogListResult,
  BlogPost,
  BlogTag,
} from "@/lib/blog-types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
export const SITE_URL = (process.env.SITE_URL ?? "http://localhost:3000").replace(
  /\/$/,
  ""
);

class BlogNotFoundError extends Error {}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store" });
  const json = await response.json().catch(() => null);
  if (response.status === 404) throw new BlogNotFoundError();
  if (!response.ok || !json?.ok) {
    throw new Error(json?.error ?? "خطا در دریافت اطلاعات وبلاگ");
  }
  return json.data as T;
}

export async function getBlogPosts(params: {
  category?: string;
  tag?: string;
  search?: string;
  page?: number;
  perPage?: number;
}): Promise<BlogListResult> {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.tag) query.set("tag", params.tag);
  if (params.search) query.set("search", params.search);
  if (params.page) query.set("page", String(params.page));
  if (params.perPage) query.set("perPage", String(params.perPage));
  return apiGet<BlogListResult>(`/api/blog/posts?${query}`);
}

export async function getBlogTaxonomies(): Promise<{
  categories: BlogCategory[];
  tags: BlogTag[];
}> {
  const [categoryData, tagData] = await Promise.all([
    apiGet<{ categories: BlogCategory[] }>("/api/blog/categories"),
    apiGet<{ tags: BlogTag[] }>("/api/blog/tags"),
  ]);
  return { categories: categoryData.categories, tags: tagData.tags };
}

export const getBlogPost = cache(async (slug: string): Promise<BlogPost | null> => {
  try {
    const data = await apiGet<{ post: BlogPost }>(
      `/api/blog/posts/${encodeURIComponent(slug)}`
    );
    return data.post;
  } catch (error) {
    if (error instanceof BlogNotFoundError) return null;
    throw error;
  }
});

export function absoluteMediaUrl(path: string | null): string | undefined {
  return path ? new URL(path, SITE_URL).toString() : undefined;
}
