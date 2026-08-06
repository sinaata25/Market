import Link from "next/link";
import type { BlogPost } from "@/lib/blog-types";
import BlogImage from "@/components/blog/BlogImage";

function faDate(value: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogCard({ post }: { post: BlogPost }) {
  return (
    <article className="group overflow-hidden rounded-2xl border border-slate-100 bg-white transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md">
      <Link href={`/blog/${post.slug}`} className="block aspect-[16/9] overflow-hidden">
        <BlogImage
          src={post.featuredImage}
          alt={post.title}
          className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]"
        />
      </Link>
      <div className="p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
          {post.category && (
            <Link
              href={`/blog?category=${encodeURIComponent(post.category.slug)}`}
              className="rounded-full bg-brand-50 px-2.5 py-1 font-medium text-brand-700 hover:bg-brand-100"
            >
              {post.category.name}
            </Link>
          )}
          <time dateTime={post.publishedAt ?? undefined}>{faDate(post.publishedAt)}</time>
        </div>
        <h2 className="text-base font-bold leading-7 text-slate-800 transition group-hover:text-brand-700">
          <Link href={`/blog/${post.slug}`}>{post.title}</Link>
        </h2>
        <p className="mt-2 line-clamp-3 text-sm leading-7 text-slate-500">
          {post.excerpt}
        </p>
        <div className="mt-4 flex items-center justify-between border-t border-slate-50 pt-3 text-xs">
          <span className="text-slate-400">نویسنده: {post.author.name}</span>
          <Link href={`/blog/${post.slug}`} className="font-medium text-brand-600">
            ادامه مطلب ←
          </Link>
        </div>
      </div>
    </article>
  );
}
