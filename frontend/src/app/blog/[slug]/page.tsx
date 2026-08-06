import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import BlogImage from "@/components/blog/BlogImage";
import JsonLd from "@/components/seo/JsonLd";
import {
  absoluteMediaUrl,
  getBlogPost,
  SITE_URL,
} from "@/lib/blog";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getBlogPost(slug);
  if (!post) {
    return {
      title: "نوشته یافت نشد",
      robots: { index: false, follow: false },
    };
  }
  const title = post.seoTitle || post.title;
  const description = post.seoDescription || post.excerpt;
  const image = absoluteMediaUrl(post.featuredImage);
  const canonical = `${SITE_URL}/blog/${encodeURIComponent(post.slug)}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: {
      title,
      description,
      type: "article",
      locale: "fa_IR",
      url: canonical,
      publishedTime: post.publishedAt ?? undefined,
      authors: [post.author.name],
      ...(image ? { images: [{ url: image, alt: post.title }] } : {}),
    },
    twitter: {
      card: image ? "summary_large_image" : "summary",
      title,
      description,
      ...(image ? { images: [image] } : {}),
    },
  };
}

function faDate(value: string | null) {
  return value
    ? new Date(value).toLocaleDateString("fa-IR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "";
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getBlogPost(slug);
  if (!post || !post.content) notFound();

  const canonical = `${SITE_URL}/blog/${encodeURIComponent(post.slug)}`;
  const image = absoluteMediaUrl(post.featuredImage);
  const articleSchema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.seoDescription || post.excerpt,
    image: image ? [image] : undefined,
    datePublished: post.publishedAt,
    dateModified: post.updatedAt ?? post.publishedAt,
    author: { "@type": "Person", name: post.author.name },
    mainEntityOfPage: canonical,
  };

  return (
    <article className="mx-auto max-w-5xl px-4 py-7">
      <JsonLd data={articleSchema} />
      <nav className="mb-5 flex flex-wrap items-center gap-1 text-xs text-slate-400" aria-label="مسیر صفحه">
        <Link href="/" className="hover:text-brand-600">خانه</Link>
        <span>/</span>
        <Link href="/blog" className="hover:text-brand-600">وبلاگ</Link>
        {post.category && <><span>/</span><Link href={`/blog?category=${encodeURIComponent(post.category.slug)}`} className="hover:text-brand-600">{post.category.name}</Link></>}
        <span>/</span>
        <span className="max-w-[260px] truncate text-slate-600">{post.title}</span>
      </nav>

      <header className="rounded-3xl border border-slate-100 bg-white px-5 py-7 text-center sm:px-10 sm:py-10">
        {post.category && (
          <Link href={`/blog?category=${encodeURIComponent(post.category.slug)}`} className="inline-block rounded-full bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700">
            {post.category.name}
          </Link>
        )}
        <h1 className="mx-auto mt-4 max-w-3xl text-2xl font-bold leading-[1.8] text-slate-800 sm:text-3xl">{post.title}</h1>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-500">{post.excerpt}</p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3 text-xs text-slate-400">
          <span>نویسنده: {post.author.name}</span>
          <span aria-hidden>•</span>
          <time dateTime={post.publishedAt ?? undefined}>{faDate(post.publishedAt)}</time>
        </div>
      </header>

      <div className="mt-6 overflow-hidden rounded-3xl">
        <BlogImage src={post.featuredImage} alt={post.title} className="aspect-[16/8] w-full object-cover" />
      </div>

      <div className="mt-6 rounded-3xl border border-slate-100 bg-white px-5 py-8 sm:px-10">
        <div className="whitespace-pre-wrap text-base leading-9 text-slate-700">{post.content}</div>
        {post.tags.length > 0 && (
          <footer className="mt-10 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-6 text-xs">
            <span className="text-slate-400">برچسب‌ها:</span>
            {post.tags.map((tag) => (
              <Link key={tag.id} href={`/blog?tag=${encodeURIComponent(tag.slug)}`} className="rounded-lg bg-slate-100 px-3 py-1.5 text-slate-600 hover:bg-brand-50 hover:text-brand-700">#{tag.name}</Link>
            ))}
          </footer>
        )}
      </div>

      <div className="mt-6 text-center">
        <Link href="/blog" className="inline-block rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm text-slate-600 transition hover:border-brand-300 hover:text-brand-700">بازگشت به همه نوشته‌ها</Link>
      </div>
    </article>
  );
}
