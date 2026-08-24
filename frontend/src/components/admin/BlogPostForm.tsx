"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import BlogImage from "@/components/blog/BlogImage";
import type { BlogCategory, BlogPost, BlogTag } from "@/lib/blog-types";
import { api } from "@/lib/client-api";

type FormState = {
  title: string;
  slug: string;
  excerpt: string;
  content: string;
  categorySlug: string;
  tagSlugs: string[];
  status: "DRAFT" | "PUBLISHED";
  publishedAt: string;
  seoTitle: string;
  seoDescription: string;
};

const EMPTY: FormState = {
  title: "",
  slug: "",
  excerpt: "",
  content: "",
  categorySlug: "",
  tagSlugs: [],
  status: "DRAFT",
  publishedAt: "",
  seoTitle: "",
  seoDescription: "",
};

function inputClass() {
  return "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";
}

function localDateTime(iso: string | null) {
  if (!iso) return "";
  const date = new Date(iso);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function nowLocal() {
  return localDateTime(new Date().toISOString());
}

export default function BlogPostForm({ postId }: { postId?: number }) {
  const router = useRouter();
  const isEdit = postId !== undefined;
  const fileRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [featuredImage, setFeaturedImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  useEffect(() => {
    Promise.all([
      api.get<{ categories: BlogCategory[] }>("/api/admin/blog/categories"),
      api.get<{ tags: BlogTag[] }>("/api/admin/blog/tags"),
    ]).then(([categoryResult, tagResult]) => {
      if (categoryResult.ok) setCategories(categoryResult.data?.categories ?? []);
      if (tagResult.ok) setTags(tagResult.data?.tags ?? []);
    });
    if (!isEdit) return;
    api.get<{ post: BlogPost }>(`/api/admin/blog/posts/${postId}`).then((result) => {
      if (result.ok && result.data) {
        const post = result.data.post;
        setForm({
          title: post.title,
          slug: post.slug,
          excerpt: post.excerpt,
          content: post.content ?? "",
          categorySlug: post.category?.slug ?? "",
          tagSlugs: post.tags.map((tag) => tag.slug),
          status: post.status,
          publishedAt: localDateTime(post.publishedAt),
          seoTitle: post.seoTitle,
          seoDescription: post.seoDescription,
        });
        setFeaturedImage(post.featuredImage);
      } else {
        setMessage({ ok: false, text: result.error ?? "نوشته یافت نشد" });
      }
      setLoading(false);
    });
  }, [isEdit, postId]);

  function toggleTag(slug: string) {
    setForm((current) => ({
      ...current,
      tagSlugs: current.tagSlugs.includes(slug)
        ? current.tagSlugs.filter((item) => item !== slug)
        : [...current.tagSlugs, slug],
    }));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    const payload = {
      ...form,
      title: form.title.trim(),
      slug: form.slug.trim(),
      excerpt: form.excerpt.trim(),
      content: form.content.trim(),
      categorySlug: form.categorySlug || null,
      publishedAt: form.status === "PUBLISHED" && form.publishedAt
        ? new Date(form.publishedAt).toISOString()
        : null,
      seoTitle: form.seoTitle.trim(),
      seoDescription: form.seoDescription.trim(),
    };
    const result = isEdit
      ? await api.patch<{ post: BlogPost }>(`/api/admin/blog/posts/${postId}`, payload)
      : await api.post<{ post: BlogPost }>("/api/admin/blog/posts", payload);
    setSaving(false);
    if (!result.ok || !result.data) {
      setMessage({ ok: false, text: result.error ?? "ذخیره نوشته انجام نشد" });
      return;
    }
    if (!isEdit) {
      router.push(`/admin/blog/${result.data.post.id}`);
      return;
    }
    setForm((current) => ({
      ...current,
      slug: result.data?.post.slug ?? current.slug,
      publishedAt: localDateTime(result.data?.post.publishedAt ?? null),
    }));
    setMessage({ ok: true, text: "تغییرات نوشته ذخیره شد ✅" });
  }

  async function uploadImage(file: File) {
    setUploading(true);
    setMessage(null);
    const data = new FormData();
    data.append("file", file);
    const result = await api.upload<{ post: BlogPost }>(
      `/api/admin/blog/posts/${postId}/featured-image`,
      data
    );
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
    if (result.ok && result.data) {
      setFeaturedImage(result.data.post.featuredImage);
      setMessage({ ok: true, text: "تصویر شاخص ذخیره شد ✅" });
    } else {
      setMessage({ ok: false, text: result.error ?? "آپلود تصویر انجام نشد" });
    }
  }

  async function removeImage() {
    if (!confirm("تصویر شاخص حذف شود؟")) return;
    const result = await api.delete(`/api/admin/blog/posts/${postId}/featured-image`);
    if (result.ok) setFeaturedImage(null);
    else setMessage({ ok: false, text: result.error ?? "حذف تصویر انجام نشد" });
  }

  if (loading) {
    return <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">در حال بارگذاری...</div>;
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="min-w-0 space-y-4 rounded-2xl border border-slate-100 bg-white p-5 lg:col-span-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">عنوان نوشته *</label>
            <input required maxLength={255} value={form.title} onChange={(event) => set("title", event.target.value)} className={inputClass()} />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">نامک</label>
            <input dir="ltr" value={form.slug} onChange={(event) => set("slug", event.target.value)} className={inputClass()} placeholder="خالی بگذارید تا خودکار ساخته شود" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">خلاصه *</label>
            <textarea required maxLength={500} rows={3} value={form.excerpt} onChange={(event) => set("excerpt", event.target.value)} className={`${inputClass()} resize-y leading-7`} />
            <p className="mt-1 text-left text-[10px] text-slate-400 font-num">{form.excerpt.length.toLocaleString("fa-IR")} / ۵۰۰</p>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">محتوای نوشته *</label>
            <textarea required rows={18} value={form.content} onChange={(event) => set("content", event.target.value)} className={`${inputClass()} resize-y whitespace-pre-wrap leading-8`} placeholder="متن ساده بنویسید؛ فاصله خطوط و پاراگراف‌ها در صفحه حفظ می‌شود." />
            <p className="mt-1 text-[10px] text-slate-400">محتوا به‌صورت متن ساده و امن نمایش داده می‌شود؛ HTML اجرا نخواهد شد.</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">وضعیت</label>
              <select
                value={form.status}
                onChange={(event) => {
                  const status = event.target.value as FormState["status"];
                  setForm((current) => ({
                    ...current,
                    status,
                    publishedAt: status === "PUBLISHED" ? current.publishedAt || nowLocal() : "",
                  }));
                }}
                className={inputClass()}
              >
                <option value="DRAFT">پیش‌نویس</option>
                <option value="PUBLISHED">منتشرشده</option>
              </select>
            </div>
            {form.status === "PUBLISHED" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">زمان انتشار *</label>
                <input required type="datetime-local" value={form.publishedAt} onChange={(event) => set("publishedAt", event.target.value)} className={`${inputClass()} font-num`} />
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">دسته‌بندی</label>
              <select value={form.categorySlug} onChange={(event) => set("categorySlug", event.target.value)} className={inputClass()}>
                <option value="">بدون دسته‌بندی</option>
                {categories.map((category) => <option key={category.id} value={category.slug}>{category.name}</option>)}
              </select>
            </div>
            <div>
              <span className="mb-2 block text-xs font-medium text-slate-600">برچسب‌ها</span>
              <div className="max-h-40 space-y-2 overflow-y-auto rounded-xl border border-slate-100 p-3">
                {tags.length === 0 ? <p className="text-[11px] text-slate-400">هنوز برچسبی ساخته نشده است.</p> : tags.map((tag) => (
                  <label key={tag.id} className="flex cursor-pointer items-center gap-2 text-xs text-slate-600">
                    <input type="checkbox" checked={form.tagSlugs.includes(tag.slug)} onChange={() => toggleTag(tag.slug)} className="accent-brand-600" />
                    {tag.name}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {isEdit && (
            <div className="rounded-2xl border border-slate-100 bg-white p-5">
              <span className="mb-3 block text-xs font-medium text-slate-600">تصویر شاخص</span>
              <BlogImage src={featuredImage} alt={form.title || "تصویر شاخص"} className="aspect-[16/9] w-full rounded-xl object-cover" />
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; if (file) uploadImage(file); }} />
              <button type="button" disabled={uploading} onClick={() => fileRef.current?.click()} className="mt-3 w-full rounded-xl border border-dashed border-slate-300 py-2.5 text-xs text-slate-500 hover:border-brand-400 disabled:opacity-50">
                {uploading ? "در حال آپلود..." : "آپلود JPEG، PNG یا WebP (حداکثر ۵MB)"}
              </button>
              {featuredImage && <button type="button" onClick={removeImage} className="mt-2 w-full text-xs text-red-400 hover:text-red-600">حذف تصویر</button>}
            </div>
          )}

          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">عنوان سئو</label>
              <input maxLength={200} value={form.seoTitle} onChange={(event) => set("seoTitle", event.target.value)} className={inputClass()} placeholder="در صورت خالی بودن، عنوان نوشته" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">توضیحات سئو</label>
              <textarea maxLength={320} rows={4} value={form.seoDescription} onChange={(event) => set("seoDescription", event.target.value)} className={`${inputClass()} resize-y leading-6`} placeholder="در صورت خالی بودن، خلاصه نوشته" />
            </div>
          </div>
        </div>
      </div>

      {message && <p className={`rounded-xl px-4 py-3 text-xs ${message.ok ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-500"}`}>{message.text}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <button disabled={saving} className="rounded-xl bg-brand-600 px-8 py-3 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-60">{saving ? "در حال ذخیره..." : isEdit ? "ذخیره تغییرات" : "ایجاد نوشته"}</button>
        <button type="button" onClick={() => router.push("/admin/blog")} className="rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm text-slate-600">بازگشت</button>
      </div>
    </form>
  );
}
