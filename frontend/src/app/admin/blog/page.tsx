"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { EmptyRow, faDateTime, faNum, Pager } from "@/components/admin/ui";
import type { BlogPost } from "@/lib/blog-types";
import { api } from "@/lib/client-api";

const STATUS = {
  DRAFT: { label: "پیش‌نویس", className: "bg-amber-50 text-amber-700" },
  PUBLISHED: { label: "منتشرشده", className: "bg-emerald-50 text-emerald-700" },
};

export default function AdminBlogPage() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    const query = new URLSearchParams({ page: String(page) });
    if (search.trim()) query.set("search", search.trim());
    if (status) query.set("status", status);
    api.get<{ posts: BlogPost[]; pages: number; total: number }>(`/api/admin/blog/posts?${query}`).then((result) => {
      if (result.ok && result.data) {
        setPosts(result.data.posts);
        setPages(result.data.pages);
        setTotal(result.data.total);
      } else {
        setMessage(result.error ?? "دریافت نوشته‌ها انجام نشد");
      }
      setLoading(false);
    });
  }, [page, search, status]);

  useEffect(() => { load(); }, [load]);

  function notify(text: string) {
    setMessage(text);
    window.setTimeout(() => setMessage(""), 4000);
  }

  async function togglePublication(post: BlogPost) {
    const action = post.status === "PUBLISHED" ? "unpublish" : "publish";
    const result = await api.post(`/api/admin/blog/posts/${post.id}/${action}`, {});
    if (result.ok) {
      notify(action === "publish" ? "نوشته منتشر شد ✅" : "نوشته به پیش‌نویس برگشت");
      load();
    } else notify(result.error ?? "تغییر وضعیت انجام نشد");
  }

  async function remove(post: BlogPost) {
    if (!confirm(`نوشته «${post.title}» برای همیشه حذف شود؟`)) return;
    const result = await api.delete(`/api/admin/blog/posts/${post.id}`);
    if (result.ok) {
      notify("نوشته حذف شد ✅");
      load();
    } else notify(result.error ?? "حذف نوشته انجام نشد");
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">نوشته‌های وبلاگ <span className="text-sm font-normal text-slate-400">({faNum(total)})</span></h1>
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/admin/blog/taxonomies" className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs text-slate-600 hover:border-brand-300">دسته‌ها و برچسب‌ها</Link>
          <Link href="/admin/blog/new" className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white hover:bg-brand-700">+ نوشته جدید</Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-100 bg-white p-3">
        <input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="جستجوی نوشته..." className="w-full min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-2 text-xs outline-none focus:border-brand-400 sm:min-w-48" />
        <select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none">
          <option value="">همه وضعیت‌ها</option>
          <option value="DRAFT">پیش‌نویس</option>
          <option value="PUBLISHED">منتشرشده</option>
        </select>
      </div>

      {message && <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">{message}</p>}

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[760px] text-sm">
          <thead><tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
            <th className="px-5 py-3 font-medium">عنوان</th><th className="px-3 py-3 font-medium">دسته</th><th className="px-3 py-3 font-medium">وضعیت</th><th className="px-3 py-3 font-medium">زمان انتشار</th><th className="px-5 py-3 font-medium">عملیات</th>
          </tr></thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? <EmptyRow colSpan={5} text="در حال بارگذاری..." /> : posts.length === 0 ? <EmptyRow colSpan={5} text="نوشته‌ای یافت نشد" /> : posts.map((post) => {
              const badge = STATUS[post.status];
              return (
                <tr key={post.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3"><p className="max-w-[280px] truncate text-xs font-medium text-slate-700">{post.title}</p><p className="mt-1 max-w-[280px] truncate text-[10px] text-slate-400" dir="ltr">/blog/{post.slug}</p></td>
                  <td className="px-3 py-3 text-xs text-slate-500">{post.category?.name ?? "—"}</td>
                  <td className="px-3 py-3"><span className={`rounded-lg px-2.5 py-1 text-[11px] font-medium ${badge.className}`}>{badge.label}</span></td>
                  <td className="px-3 py-3 text-xs text-slate-500">{post.publishedAt ? faDateTime(post.publishedAt) : "—"}</td>
                  <td className="px-5 py-3"><div className="flex items-center gap-3 text-xs">
                    <Link href={`/admin/blog/${post.id}`} className="text-brand-600 hover:underline">ویرایش</Link>
                    {post.status === "PUBLISHED" && <Link href={`/blog/${post.slug}`} target="_blank" className="text-slate-500 hover:underline">مشاهده</Link>}
                    <button onClick={() => togglePublication(post)} className="text-blue-500 hover:underline">{post.status === "PUBLISHED" ? "عدم انتشار" : "انتشار"}</button>
                    <button onClick={() => remove(post)} className="text-red-400 hover:text-red-600">حذف</button>
                  </div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <Pager page={page} pages={pages} onPage={setPage} />
    </div>
  );
}
