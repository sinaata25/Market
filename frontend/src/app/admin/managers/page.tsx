"use client";

// مدیریت حساب‌های «مدیر اجرایی» — فقط سوپریوزر (ناحیه‌ی توسعه‌دهنده)
// مدیر اجرایی خودش هرگز به این صفحه نمی‌رسد و نمی‌تواند نقش ممتاز بسازد.

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { EmptyRow, faNum } from "@/components/admin/ui";

type Manager = {
  id: number;
  phone: string;
  name: string | null;
  isActive: boolean;
  /** دسترسی پنل سئو — فقط از همین صفحه (یعنی فقط مدیر سیستم) داده می‌شود */
  canAccessSeo: boolean;
  createdAt: string;
};

type Draft = { phone: string; name: string; canAccessSeo: boolean };

const EMPTY_DRAFT: Draft = { phone: "", name: "", canAccessSeo: false };

export default function AdminManagers() {
  const [rows, setRows] = useState<Manager[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [editing, setEditing] = useState<Manager | null>(null);

  const load = useCallback(() => {
    api.get<{ managers: Manager[] }>("/api/admin/managers").then((res) => {
      if (res.ok && res.data) setRows(res.data.managers);
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
    const res = await api.post<{ manager: Manager }>(
      "/api/admin/managers",
      {
        phone: draft.phone.trim(),
        name: draft.name.trim(),
        canAccessSeo: draft.canAccessSeo,
      }
    );
    setSaving(false);
    if (!res.ok) {
      setError(res.error ?? "ساخت مدیر اجرایی ناموفق بود");
      return;
    }
    setDraft(EMPTY_DRAFT);
    flash("مدیر اجرایی ساخته شد");
    load();
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    const res = await api.patch<{ manager: Manager }>(
      `/api/admin/managers/${editing.id}`,
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

  async function toggleActive(row: Manager) {
    const res = await api.patch(`/api/admin/managers/${row.id}`, {
      isActive: !row.isActive,
    });
    if (!res.ok) {
      setError(res.error ?? "تغییر وضعیت ناموفق بود");
      return;
    }
    flash(row.isActive ? "حساب غیرفعال شد" : "حساب فعال شد");
    load();
  }

  async function toggleSeoAccess(row: Manager) {
    const res = await api.patch(`/api/admin/managers/${row.id}`, {
      canAccessSeo: !row.canAccessSeo,
    });
    if (!res.ok) {
      setError(res.error ?? "تغییر دسترسی سئو ناموفق بود");
      return;
    }
    flash(
      row.canAccessSeo
        ? "دسترسی سئو گرفته شد"
        : "دسترسی سئو داده شد؛ حالا پنل سئو و ساخت مدیر سئو برایش باز است"
    );
    load();
  }

  async function revoke(row: Manager) {
    const res = await api.delete(`/api/admin/managers/${row.id}`);
    if (!res.ok) {
      setError(res.error ?? "لغو نقش ناموفق بود");
      return;
    }
    flash("نقش اجرایی لغو شد؛ حساب به مشتری عادی تبدیل شد");
    load();
  }

  const field =
    "w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          مدیران اجرایی{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(rows.length)})
          </span>
        </h1>
      </div>

      <p className="rounded-2xl border border-slate-100 bg-white p-4 text-xs leading-6 text-slate-500">
        مدیر اجرایی به همه‌ی بخش‌های کسب‌وکار (سفارش‌ها، محصولات، کاربران،
        محتوا و ...) دسترسی دارد و می‌تواند «مدیر عادی» و «مشتری» بسازد؛ اما
        سوپریوزرها را نمی‌بیند، مدیر اجرایی دیگری نمی‌سازد و به ناحیه‌ی سیستمی
        — همین صفحه و ادمین جنگو — راه ندارد.
        <br />
        <b className="font-medium text-slate-600">دسترسی سئو</b> را فقط از
        همین‌جا می‌توان داد یا گرفت. با روشن‌کردنش، آن مدیر اجرایی پنل سئو را
        می‌بیند و می‌تواند «مدیر سئو» بسازد؛ ولی همچنان نمی‌تواند این دسترسی را
        به خودش یا مدیر اجرایی دیگری بدهد. ورود این حساب‌ها هم مثل بقیه با کد
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
        className="grid gap-3 rounded-2xl border border-slate-100 bg-white p-4 sm:grid-cols-[1fr_1fr_auto_auto]"
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
            placeholder="نام مدیر اجرایی"
            className={field}
          />
        </label>
        <label className="flex items-center gap-2 self-end pb-2.5 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={draft.canAccessSeo}
            onChange={(e) =>
              setDraft({ ...draft, canAccessSeo: e.target.checked })
            }
          />
          دسترسی سئو
        </label>
        <button
          type="submit"
          disabled={saving}
          className="self-end rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:opacity-50"
        >
          افزودن مدیر اجرایی
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
              <th className="px-3 py-3 font-medium">دسترسی سئو</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={6} text="در حال بارگذاری..." />
            ) : rows.length === 0 ? (
              <EmptyRow colSpan={6} text="هنوز مدیر اجرایی‌ای ساخته نشده است" />
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
                  <td className="px-3 py-3">
                    {row.canAccessSeo ? (
                      <span className="rounded-lg bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-600">
                        دارد
                      </span>
                    ) : (
                      <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] text-slate-500">
                        ندارد
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
                        onClick={() => toggleSeoAccess(row)}
                        className="rounded-lg border border-amber-200 px-3 py-1.5 text-[11px] text-amber-600 transition hover:border-amber-400"
                      >
                        {row.canAccessSeo ? "گرفتن دسترسی سئو" : "دادن دسترسی سئو"}
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
