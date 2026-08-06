"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { BlogCategory, BlogTag } from "@/lib/blog-types";
import { api } from "@/lib/client-api";

function inputClass() {
  return "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-brand-400 focus:bg-white";
}

export default function BlogTaxonomiesPage() {
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [categoryForm, setCategoryForm] = useState({ name: "", slug: "", description: "" });
  const [tagForm, setTagForm] = useState({ name: "", slug: "" });
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    Promise.all([
      api.get<{ categories: BlogCategory[] }>("/api/admin/blog/categories"),
      api.get<{ tags: BlogTag[] }>("/api/admin/blog/tags"),
    ]).then(([categoryResult, tagResult]) => {
      if (categoryResult.ok) setCategories(categoryResult.data?.categories ?? []);
      if (tagResult.ok) setTags(tagResult.data?.tags ?? []);
    });
  }, []);

  useEffect(() => { load(); }, [load]);

  function notify(text: string) {
    setMessage(text);
    window.setTimeout(() => setMessage(""), 4000);
  }

  async function addCategory(event: React.FormEvent) {
    event.preventDefault();
    const result = await api.post("/api/admin/blog/categories", categoryForm);
    if (result.ok) {
      setCategoryForm({ name: "", slug: "", description: "" });
      notify("دسته‌بندی ساخته شد ✅");
      load();
    } else notify(result.error ?? "ساخت دسته‌بندی انجام نشد");
  }

  async function addTag(event: React.FormEvent) {
    event.preventDefault();
    const result = await api.post("/api/admin/blog/tags", tagForm);
    if (result.ok) {
      setTagForm({ name: "", slug: "" });
      notify("برچسب ساخته شد ✅");
      load();
    } else notify(result.error ?? "ساخت برچسب انجام نشد");
  }

  async function remove(kind: "categories" | "tags", id: number, name: string) {
    if (!confirm(`«${name}» حذف شود؟ ارتباط آن با نوشته‌ها نیز حذف می‌شود.`)) return;
    const result = await api.delete(`/api/admin/blog/${kind}/${id}`);
    if (result.ok) {
      notify("حذف شد ✅");
      load();
    } else notify(result.error ?? "حذف انجام نشد");
  }

  async function editCategory(category: BlogCategory) {
    const name = window.prompt("نام دسته‌بندی", category.name)?.trim();
    if (!name) return;
    const slug = window.prompt("نامک دسته‌بندی", category.slug)?.trim();
    if (slug === undefined) return;
    const description = window.prompt("توضیحات دسته‌بندی", category.description)?.trim();
    if (description === undefined) return;
    const result = await api.patch(`/api/admin/blog/categories/${category.id}`, {
      name,
      slug,
      description,
    });
    if (result.ok) {
      notify("دسته‌بندی ویرایش شد ✅");
      load();
    } else notify(result.error ?? "ویرایش دسته‌بندی انجام نشد");
  }

  async function editTag(tag: BlogTag) {
    const name = window.prompt("نام برچسب", tag.name)?.trim();
    if (!name) return;
    const slug = window.prompt("نامک برچسب", tag.slug)?.trim();
    if (slug === undefined) return;
    const result = await api.patch(`/api/admin/blog/tags/${tag.id}`, { name, slug });
    if (result.ok) {
      notify("برچسب ویرایش شد ✅");
      load();
    } else notify(result.error ?? "ویرایش برچسب انجام نشد");
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">دسته‌ها و برچسب‌های وبلاگ</h1>
        <Link href="/admin/blog" className="text-xs text-brand-600 hover:underline">بازگشت به نوشته‌ها</Link>
      </div>
      {message && <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">{message}</p>}
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="mb-4 font-bold text-slate-700">دسته‌بندی‌ها</h2>
          <form onSubmit={addCategory} className="space-y-3 border-b border-slate-100 pb-5">
            <input required maxLength={100} value={categoryForm.name} onChange={(event) => setCategoryForm((form) => ({ ...form, name: event.target.value }))} className={inputClass()} placeholder="نام دسته‌بندی" />
            <input dir="ltr" value={categoryForm.slug} onChange={(event) => setCategoryForm((form) => ({ ...form, slug: event.target.value }))} className={inputClass()} placeholder="نامک (اختیاری)" />
            <textarea rows={2} value={categoryForm.description} onChange={(event) => setCategoryForm((form) => ({ ...form, description: event.target.value }))} className={`${inputClass()} resize-y`} placeholder="توضیحات (اختیاری)" />
            <button className="rounded-xl bg-brand-600 px-4 py-2.5 text-xs font-bold text-white">افزودن دسته‌بندی</button>
          </form>
          <ul className="mt-4 divide-y divide-slate-50">
            {categories.length === 0 ? <li className="py-6 text-center text-xs text-slate-400">دسته‌بندی‌ای وجود ندارد</li> : categories.map((category) => (
              <li key={category.id} className="flex items-center justify-between gap-3 py-3">
                <div><p className="text-sm text-slate-700">{category.name}</p><p className="text-[10px] text-slate-400" dir="ltr">{category.slug}</p></div>
                <div className="flex gap-3"><button onClick={() => editCategory(category)} className="text-xs text-brand-600">ویرایش</button><button onClick={() => remove("categories", category.id, category.name)} className="text-xs text-red-400">حذف</button></div>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="mb-4 font-bold text-slate-700">برچسب‌ها</h2>
          <form onSubmit={addTag} className="space-y-3 border-b border-slate-100 pb-5">
            <input required maxLength={60} value={tagForm.name} onChange={(event) => setTagForm((form) => ({ ...form, name: event.target.value }))} className={inputClass()} placeholder="نام برچسب" />
            <input dir="ltr" value={tagForm.slug} onChange={(event) => setTagForm((form) => ({ ...form, slug: event.target.value }))} className={inputClass()} placeholder="نامک (اختیاری)" />
            <button className="rounded-xl bg-brand-600 px-4 py-2.5 text-xs font-bold text-white">افزودن برچسب</button>
          </form>
          <ul className="mt-4 divide-y divide-slate-50">
            {tags.length === 0 ? <li className="py-6 text-center text-xs text-slate-400">برچسبی وجود ندارد</li> : tags.map((tag) => (
              <li key={tag.id} className="flex items-center justify-between gap-3 py-3">
                <div><p className="text-sm text-slate-700">#{tag.name}</p><p className="text-[10px] text-slate-400" dir="ltr">{tag.slug}</p></div>
                <div className="flex gap-3"><button onClick={() => editTag(tag)} className="text-xs text-brand-600">ویرایش</button><button onClick={() => remove("tags", tag.id, tag.name)} className="text-xs text-red-400">حذف</button></div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
