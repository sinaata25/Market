"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { faNum, EmptyRow } from "@/components/admin/ui";

type Redirect = {
  id: number;
  fromPath: string;
  toPath: string;
  statusCode: number;
  isActive: boolean;
  note: string;
  hits: number;
};

const inputCls =
  "rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs outline-none transition focus:border-brand-400 focus:bg-white";

export default function SeoRedirects() {
  const [redirects, setRedirects] = useState<Redirect[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ fromPath: "", toPath: "", statusCode: 301 });
  const [message, setMessage] = useState("");

  const load = useCallback(() => {
    api.get<{ redirects: Redirect[] }>("/api/admin/seo/redirects").then((res) => {
      if (res.ok && res.data) setRedirects(res.data.redirects);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    const res = await api.post("/api/admin/seo/redirects", form);
    if (res.ok) {
      setForm({ fromPath: "", toPath: "", statusCode: 301 });
      load();
    } else {
      setMessage(res.error ?? "خطا در ثبت");
    }
  }

  async function toggle(r: Redirect) {
    await api.patch(`/api/admin/seo/redirects/${r.id}`, {
      fromPath: r.fromPath,
      toPath: r.toPath,
      statusCode: r.statusCode,
      isActive: !r.isActive,
      note: r.note,
    });
    load();
  }

  async function remove(r: Redirect) {
    if (!confirm(`ریدایرکت ${r.fromPath} حذف شود؟`)) return;
    await api.delete(`/api/admin/seo/redirects/${r.id}`);
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">
        ↪️ ریدایرکت‌ها{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({faNum(redirects.length)})
        </span>
      </h1>

      {/* فرم افزودن */}
      <form
        onSubmit={create}
        className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-100 bg-white p-4"
      >
        <div className="w-full min-w-0 flex-1 sm:min-w-40">
          <label className="mb-1 block text-[11px] text-slate-500">
            از مسیر
          </label>
          <input
            required
            dir="ltr"
            value={form.fromPath}
            onChange={(e) => setForm({ ...form, fromPath: e.target.value })}
            placeholder="/old-page"
            className={`${inputCls} w-full`}
          />
        </div>
        <div className="w-full min-w-0 flex-1 sm:min-w-40">
          <label className="mb-1 block text-[11px] text-slate-500">
            به مسیر
          </label>
          <input
            required
            dir="ltr"
            value={form.toPath}
            onChange={(e) => setForm({ ...form, toPath: e.target.value })}
            placeholder="/new-page"
            className={`${inputCls} w-full`}
          />
        </div>
        <div className="min-w-0 flex-1 sm:flex-none">
          <label className="mb-1 block text-[11px] text-slate-500">نوع</label>
          <select
            value={form.statusCode}
            onChange={(e) =>
              setForm({ ...form, statusCode: Number(e.target.value) })
            }
            className={`${inputCls} w-full`}
          >
            <option value={301}>۳۰۱ دائمی</option>
            <option value={302}>۳۰۲ موقت</option>
          </select>
        </div>
        <button
          type="submit"
          className="min-h-11 flex-1 rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 sm:flex-none"
        >
          + افزودن
        </button>
        {message && <p className="w-full text-xs text-red-500">{message}</p>}
      </form>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[600px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">از مسیر</th>
              <th className="px-3 py-3 font-medium">به مسیر</th>
              <th className="px-3 py-3 font-medium">نوع</th>
              <th className="px-3 py-3 font-medium">استفاده</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={6} text="در حال بارگذاری..." />
            ) : redirects.length === 0 ? (
              <EmptyRow colSpan={6} text="ریدایرکتی ثبت نشده است" />
            ) : (
              redirects.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3">
                    <code dir="ltr" className="text-xs text-slate-600">
                      {r.fromPath}
                    </code>
                    {r.note && (
                      <p className="mt-0.5 text-[10px] text-slate-400">
                        {r.note}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-3">
                    <code dir="ltr" className="text-xs text-brand-600">
                      {r.toPath}
                    </code>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500 font-num">
                    {faNum(r.statusCode)}
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500 font-num">
                    {faNum(r.hits)} بار
                  </td>
                  <td className="px-3 py-3">
                    <button
                      onClick={() => toggle(r)}
                      className={`rounded-lg px-2.5 py-1 text-[11px] font-medium transition ${
                        r.isActive
                          ? "bg-emerald-50 text-emerald-600"
                          : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      {r.isActive ? "فعال" : "غیرفعال"}
                    </button>
                  </td>
                  <td className="px-5 py-3">
                    <button
                      onClick={() => remove(r)}
                      className="text-xs text-red-400 hover:text-red-600"
                    >
                      حذف
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
