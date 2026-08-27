"use client";

// مدیریت حساب‌های «مدیر سئو»
//
// دسترسی: مدیر سیستم، یا مدیر اجرایی‌ای که مدیر سیستم به او دسترسی سئو داده
// است. مسیر عمداً بیرون از /admin/seo است: آنجا داده‌ی سئو مدیریت می‌شود و
// اینجا حسابِ کسی که آن داده را مدیریت می‌کند.

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { EmptyRow, faNum } from "@/components/admin/ui";

type SeoAdmin = {
  id: number;
  phone: string;
  name: string | null;
  isActive: boolean;
  createdAt: string;
};

type Draft = { phone: string; name: string };

const EMPTY_DRAFT: Draft = { phone: "", name: "" };

export default function AdminSeoAdmins() {
  const [rows, setRows] = useState<SeoAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [editing, setEditing] = useState<SeoAdmin | null>(null);

  const load = useCallback(() => {
    api.get<{ seoAdmins: SeoAdmin[] }>("/api/admin/seo-admins").then((res) => {
      if (res.ok && res.data) setRows(res.data.seoAdmins);
      else setError(res.error ?? "خطا در دریافت اطلاعات");
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function flash(message: string) {
    setNotice(message);
    setError("");
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    const res = await api.post<{ seoAdmin: SeoAdmin }>(
      "/api/admin/seo-admins",
      { phone: draft.phone.trim(), name: draft.name.trim() }
    );
    setSaving(false);
    if (!res.ok) {
      setError(res.error ?? "ساخت مدیر سئو ناموفق بود");
      return;
    }
    setDraft(EMPTY_DRAFT);
    flash("مدیر سئو ساخته شد");
    load();
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    const res = await api.patch<{ seoAdmin: SeoAdmin }>(
      `/api/admin/seo-admins/${editing.id}`,
      { phone: editing.phone.trim(), name: editing.name?.trim() ?? "" }
    );
    setSaving(false);
    if (!res.ok) {
      setError(res.error ?? "ویرایش ناموفق بود");
      return;
    }
    setEditing(null);
    flash("اطلاعات حساب به‌روزرسانی شد");
    load();
  }

  async function toggleActive(row: SeoAdmin) {
    const res = await api.patch(`/api/admin/seo-admins/${row.id}`, {
      isActive: !row.isActive,
    });
    if (!res.ok) {
      setError(res.error ?? "تغییر وضعیت ناموفق بود");
      return;
    }
    flash(row.isActive ? "حساب غیرفعال شد" : "حساب فعال شد");
    load();
  }

  async function revoke(row: SeoAdmin) {
    const res = await api.delete(`/api/admin/seo-admins/${row.id}`);
    if (!res.ok) {
      setError(res.error ?? "لغو نقش ناموفق بود");
      return;
    }
    flash("نقش سئو لغو شد؛ حساب به مشتری عادی تبدیل شد");
    load();
  }

  const field =
    "w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          مدیران سئو{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(rows.length)})
          </span>
        </h1>
      </div>

      <p className="rounded-2xl border border-slate-100 bg-white p-4 text-xs leading-6 text-slate-500">
        مدیر سئو فقط به «پنل سئو» دسترسی دارد و هیچ بخشی از داشبورد فروشگاه
        (سفارش‌ها، کاربران، مالی و ...) را نمی‌بیند. در مقابل، پنل سئو برای شما
        و سایر مدیران فروشگاه بسته است. ورود این حساب‌ها هم مثل بقیه با کد
        یکبارمصرفِ همان شماره موبایل انجام می‌شود.
      </p>

      {error && (
        <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-500">
          {error}
        </div>
      )}
      {notice && !error && (
        <div className="rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-600">
          {notice}
        </div>
      )}

      <form
        onSubmit={create}
        className="grid gap-3 rounded-2xl border border-slate-100 bg-white p-4 sm:grid-cols-[1fr_1fr_auto]"
      >
        <label className="block">
          <span className="mb-1 block text-[11px] text-slate-400">
            شماره موبایل
          </span>
          <input
            value={draft.phone}
            onChange={(e) => setDraft({ ...draft, phone: e.target.value })}
            placeholder="09121234567"
            dir="ltr"
            required
            className={`${field} font-num`}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-[11px] text-slate-400">
            نام (اختیاری)
          </span>
          <input
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="نام مدیر سئو"
            className={field}
          />
        </label>
        <button
          type="submit"
          disabled={saving}
          className="self-end rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          افزودن مدیر سئو
        </button>
      </form>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[620px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">نام</th>
              <th className="px-3 py-3 font-medium">شماره موبایل</th>
              <th className="px-3 py-3 font-medium">تاریخ ایجاد</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={5} text="در حال بارگذاری..." />
            ) : rows.length === 0 ? (
              <EmptyRow colSpan={5} text="هنوز مدیر سئویی ساخته نشده است" />
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3 text-xs text-slate-700">
                    {row.name ?? "—"}
                  </td>
                  <td
                    className="px-3 py-3 text-xs text-slate-500 font-num"
                    dir="ltr"
                  >
                    {row.phone}
                  </td>
                  <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
                    {new Date(row.createdAt).toLocaleDateString("fa-IR")}
                  </td>
                  <td className="px-3 py-3">
                    {row.isActive ? (
                      <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-600">
                        فعال
                      </span>
                    ) : (
                      <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] text-slate-500">
                        غیرفعال
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setEditing(row)}
                        className="rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] text-slate-600 transition hover:border-brand-400"
                      >
                        ویرایش
                      </button>
                      <button
                        onClick={() => toggleActive(row)}
                        className="rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] text-slate-600 transition hover:border-brand-400"
                      >
                        {row.isActive ? "غیرفعال‌سازی" : "فعال‌سازی"}
                      </button>
                      <button
                        onClick={() => revoke(row)}
                        className="rounded-lg border border-red-100 px-3 py-1.5 text-[11px] text-red-500 transition hover:border-red-300"
                      >
                        لغو نقش
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <form
          onSubmit={saveEdit}
          className="grid gap-3 rounded-2xl border border-brand-100 bg-brand-50/40 p-4 sm:grid-cols-[1fr_1fr_auto_auto]"
        >
          <label className="block">
            <span className="mb-1 block text-[11px] text-slate-400">
              شماره موبایل (شناسه ورود)
            </span>
            <input
              value={editing.phone}
              onChange={(e) =>
                setEditing({ ...editing, phone: e.target.value })
              }
              dir="ltr"
              required
              className={`${field} font-num`}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-[11px] text-slate-400">نام</span>
            <input
              value={editing.name ?? ""}
              onChange={(e) => setEditing({ ...editing, name: e.target.value })}
              className={field}
            />
          </label>
          <button
            type="submit"
            disabled={saving}
            className="self-end rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            ذخیره
          </button>
          <button
            type="button"
            onClick={() => setEditing(null)}
            className="self-end rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-xs text-slate-600"
          >
            انصراف
          </button>
        </form>
      )}
    </div>
  );
}
