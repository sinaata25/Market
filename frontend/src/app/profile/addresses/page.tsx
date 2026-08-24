"use client";

import { useCallback, useEffect, useState } from "react";
import ProvinceCityFields from "@/components/forms/ProvinceCityFields";
import { api } from "@/lib/client-api";

type Address = {
  id: number;
  title: string;
  fullName: string;
  phone: string;
  province: string;
  city: string;
  provinceId: string | null;
  cityId: string | null;
  address: string;
  postalCode: string;
  isDefault: boolean;
};

type Form = Omit<Address, "id">;

const EMPTY: Form = {
  title: "خانه",
  fullName: "",
  phone: "",
  province: "",
  city: "",
  provinceId: null,
  cityId: null,
  address: "",
  postalCode: "",
  isDefault: false,
};

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";

export default function MyAddresses() {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<Form | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.get<{ addresses: Address[] }>("/api/auth/addresses").then((res) => {
      if (res.ok && res.data) setAddresses(res.data.addresses);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function set<K extends keyof Form>(key: K, value: Form[K]) {
    setError("");
    setForm((f) => (f ? { ...f, [key]: value } : f));
  }

  function startAdd() {
    setForm({ ...EMPTY });
    setEditingId(null);
    setError("");
  }

  function startEdit(a: Address) {
    const { id, ...rest } = a;
    void id;
    setForm(rest);
    setEditingId(a.id);
    setError("");
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError("");
    const res = editingId
      ? await api.patch(`/api/auth/addresses/${editingId}`, form)
      : await api.post("/api/auth/addresses", form);
    setSaving(false);
    if (res.ok) {
      setForm(null);
      setEditingId(null);
      load();
    } else {
      setError(res.error ?? "خطا در ذخیره آدرس");
    }
  }

  async function remove(a: Address) {
    if (!confirm(`آدرس «${a.title}» حذف شود؟`)) return;
    await api.delete(`/api/auth/addresses/${a.id}`);
    load();
  }

  async function makeDefault(a: Address) {
    const { id, ...rest } = a;
    void id;
    await api.patch(`/api/auth/addresses/${a.id}`, {
      ...rest,
      isDefault: true,
    });
    load();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-800">آدرس‌های من</h1>
        {!form && (
          <button
            onClick={startAdd}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700"
          >
            + افزودن آدرس
          </button>
        )}
      </div>

      {/* فرم */}
      {form && (
        <form
          onSubmit={save}
          className="space-y-4 rounded-2xl border border-brand-100 bg-white p-5"
        >
          <h2 className="text-sm font-bold text-slate-700">
            {editingId ? "ویرایش آدرس" : "آدرس جدید"}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs text-slate-500">
                عنوان آدرس
              </label>
              <input
                value={form.title}
                onChange={(e) => set("title", e.target.value)}
                placeholder="خانه / محل کار"
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-slate-500">
                نام تحویل‌گیرنده *
              </label>
              <input
                required
                value={form.fullName}
                onChange={(e) => set("fullName", e.target.value)}
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-slate-500">
                شماره تماس *
              </label>
              <input
                required
                dir="ltr"
                value={form.phone}
                onChange={(e) => set("phone", e.target.value)}
                placeholder="09xxxxxxxxx"
                className={`${inputCls} text-center font-num`}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs text-slate-500">
                کد پستی
              </label>
              <input
                dir="ltr"
                value={form.postalCode}
                onChange={(e) => set("postalCode", e.target.value)}
                placeholder="۱۰ رقم (اختیاری)"
                className={`${inputCls} text-center font-num`}
              />
            </div>
            <ProvinceCityFields
              province={form.province}
              city={form.city}
              provinceId={form.provinceId}
              cityId={form.cityId}
              onChange={(location) =>
                setForm((current) =>
                  current ? { ...current, ...location } : current
                )
              }
              onClearError={() => setError("")}
              disabled={saving}
              className="grid grid-cols-1 gap-3 sm:col-span-2 sm:grid-cols-2"
              selectClassName={inputCls}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs text-slate-500">
              آدرس کامل پستی *
            </label>
            <textarea
              required
              rows={3}
              value={form.address}
              onChange={(e) => set("address", e.target.value)}
              className={`${inputCls} resize-none leading-6`}
            />
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={form.isDefault}
              onChange={(e) => set("isDefault", e.target.checked)}
              className="h-4 w-4 accent-brand-600"
            />
            این آدرس، آدرس پیش‌فرض من باشد
          </label>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-brand-600 px-6 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {saving ? "در حال ذخیره..." : "ذخیره آدرس"}
            </button>
            <button
              type="button"
              onClick={() => setForm(null)}
              className="rounded-xl border border-slate-200 px-5 py-2.5 text-xs text-slate-600"
            >
              انصراف
            </button>
          </div>
        </form>
      )}

      {/* فهرست آدرس‌ها */}
      {loading ? (
        <p className="py-10 text-center text-sm text-slate-400">
          در حال بارگذاری...
        </p>
      ) : addresses.length === 0 && !form ? (
        <div className="rounded-2xl border border-slate-100 bg-white px-6 py-16 text-center">
          <span className="mb-4 block text-5xl">📍</span>
          <p className="mb-6 text-sm text-slate-500">
            هنوز آدرسی ثبت نکرده‌اید
          </p>
          <button
            onClick={startAdd}
            className="rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
          >
            افزودن اولین آدرس
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {addresses.map((a) => (
            <div
              key={a.id}
              className={`rounded-2xl border bg-white p-5 transition ${
                a.isDefault
                  ? "border-brand-300 ring-1 ring-brand-100"
                  : "border-slate-100"
              }`}
            >
              <div className="mb-3 flex items-center gap-2">
                <span className="text-lg">📍</span>
                <span className="text-sm font-bold text-slate-700">
                  {a.title}
                </span>
                {a.isDefault && (
                  <span className="rounded-lg bg-brand-50 px-2 py-0.5 text-[10px] font-medium text-brand-700">
                    پیش‌فرض
                  </span>
                )}
              </div>
              <div className="space-y-1 text-xs leading-6 text-slate-500">
                <p className="text-slate-700">{a.fullName}</p>
                <p className="font-num" dir="ltr">
                  {a.phone}
                </p>
                <p>
                  {a.province}، {a.city}
                </p>
                <p className="line-clamp-2">{a.address}</p>
                {a.postalCode && (
                  <p className="font-num">کد پستی: {a.postalCode}</p>
                )}
              </div>
              <div className="mt-4 flex items-center gap-3 border-t border-slate-50 pt-3 text-xs">
                <button
                  onClick={() => startEdit(a)}
                  className="text-brand-600 hover:underline"
                >
                  ویرایش
                </button>
                {!a.isDefault && (
                  <button
                    onClick={() => makeDefault(a)}
                    className="text-slate-500 hover:text-brand-600"
                  >
                    پیش‌فرض کن
                  </button>
                )}
                <button
                  onClick={() => remove(a)}
                  className="mr-auto text-red-400 hover:text-red-600"
                >
                  حذف
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
