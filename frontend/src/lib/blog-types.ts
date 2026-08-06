export type BlogCategory = {
  id: number;
  name: string;
  slug: string;
  description: string;
  postsCount?: number;
};

export type BlogTag = {
  id: number;
  name: string;
  slug: string;
  postsCount?: number;
};

export type BlogPost = {
  id: number;
  title: string;
  slug: string;
  excerpt: string;
  content?: string;
  featuredImage: string | null;
  author: { id: number; name: string };
  category: BlogCategory | null;
  tags: BlogTag[];
  status: "DRAFT" | "PUBLISHED";
  publishedAt: string | null;
  createdAt?: string;
  updatedAt?: string;
  seoTitle: string;
  seoDescription: string;
};

export type BlogListResult = {
  items: BlogPost[];
  total: number;
  page: number;
  perPage: number;
  pages: number;
};
