"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { EmptyRow, faNum } from "@/components/admin/ui";
import { api } from "@/lib/client-api";
import type { Brand } from "@/lib/products";

type AdminBrand = Brand & {
  id: number;
  isActive: boolean;
  productCount: number;
};

type BrandForm = {
  name: string;
  slug: string;
  description: string;
  website: string;
};

const EMPTY_FORM: BrandForm = {
  name: "",
  slug: "",
  description: "",
  website: "",
};

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";

export default function AdminBrandsPage() {
  const [brands, setBrands] = useState<AdminBrand[]>([]);
  const [form, setForm] = useState<BrandForm>(EMPTY_FORM);
  const [editing, setEditing] = useState<AdminBrand | null>(null);
  const [logo, setLogo] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changingVisibility, setChangingVisibility] = useState<number | null>(
    null
  );
  const [adjusting, setAdjusting] = useState(false);
  const [selectedBrandId, setSelectedBrandId] = useState("");
  const [operation, setOperation] = useState<"increase" | "decrease">(
    "increase"
  );
  const [percentage, setPercentage] = useState("");
  const [message, setMessage] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const formSection = useRef<HTMLElement>(null);

  const notify = useCallback((text: string) => {
    setMessage(text);
    window.setTimeout(() => setMessage(""), 5000);
  }, []);

  const load = useCallback(async () => {
    const result = await api.get<{ brands: AdminBrand[] }>(
      "/api/admin/brands"
    );
    if (result.ok) setBrands(result.data?.brands ?? []);
    else notify(result.error ?? "دریافت برندها انجام نشد");
    setLoading(false);
  }, [notify]);

  useEffect(() => {
    let ignore = false;
    api.get<{ brands: AdminBrand[] }>("/api/admin/brands").then((result) => {
      if (ignore) return;
      if (result.ok) setBrands(result.data?.brands ?? []);
      else notify(result.error ?? "دریافت برندها انجام نشد");
      setLoading(false);
    });
    return () => {
      ignore = true;
    };
  }, [notify]);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditing(null);
    setLogo(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function startEditing(brand: AdminBrand) {
    setEditing(brand);
    setForm({
      name: brand.name,
      slug: brand.slug,
      description: brand.description ?? "",
      website: brand.website ?? "",
    });
    setLogo(null);
    if (fileInput.current) fileInput.current.value = "";
    formSection.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      slug: form.slug.trim(),
      description: form.description.trim(),
      website: form.website.trim(),
    };
    const result = editing
      ? await api.patch<{ brand: AdminBrand }>(
          `/api/admin/brands/${editing.id}`,
          payload
        )
      : await api.post<{ brand: AdminBrand }>("/api/admin/brands", payload);

    if (!result.ok || !result.data) {
      notify(result.error ?? "ذخیره برند انجام نشد");
      setSaving(false);
      return;
    }

    if (logo) {
      const logoForm = new FormData();
      logoForm.append("file", logo);
      const upload = await api.upload<{ brand: AdminBrand }>(
        `/api/admin/brands/${result.data.brand.id}/logo`,
        logoForm
      );
      if (!upload.ok) {
        notify(
          `برند ذخیره شد، اما نشان بارگذاری نشد: ${upload.error ?? "خطای نامشخص"}`
        );
        resetForm();
        setSaving(false);
        await load();
        return;
      }
    }

    notify(editing ? "برند ویرایش شد ✅" : "برند افزوده شد ✅");
    resetForm();
    setSaving(false);
    await load();
  }

  async function toggleVisibility(brand: AdminBrand) {
    if (changingVisibility !== null) return;
    setChangingVisibility(brand.id);
    const result = await api.patch<{ brand: AdminBrand }>(
      `/api/admin/brands/${brand.id}`,
      { isActive: !brand.isActive }
    );
    if (result.ok) {
      notify(
        brand.isActive
          ? "برند از فروشگاه پنهان شد ✅"
          : "برند در فروشگاه نمایش داده شد ✅"
      );
      await load();
    } else notify(result.error ?? "تغییر وضعیت برند انجام نشد");
    setChangingVisibility(null);
  }

  async function remove(brand: AdminBrand) {
    if (brand.productCount > 0) {
      notify(
        `این برند ${faNum(brand.productCount)} محصول دارد؛ ابتدا برند محصولات را تغییر دهید.`
      );
      return;
    }
    if (!window.confirm(`برند «${brand.name}» حذف شود؟ این کار قابل بازگشت نیست.`)) {
      return;
    }
    const result = await api.delete(`/api/admin/brands/${brand.id}`);
    if (result.ok) {
      if (editing?.id === brand.id) resetForm();
      if (selectedBrandId === String(brand.id)) setSelectedBrandId("");
      notify("برند حذف شد ✅");
      await load();
    } else notify(result.error ?? "حذف برند انجام نشد");
  }

  async function removeLogo(brand: AdminBrand) {
    if (!window.confirm(`نشان برند «${brand.name}» حذف شود؟`)) return;
    const result = await api.delete(`/api/admin/brands/${brand.id}/logo`);
    if (result.ok) {
      notify("نشان برند حذف شد ✅");
      await load();
    } else notify(result.error ?? "حذف نشان انجام نشد");
  }

  async function adjustPrices(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const selectedBrand = brands.find(
      (brand) => brand.id === Number(selectedBrandId)
    );
    const percentageValue = Number(percentage);
    if (!selectedBrand || !Number.isFinite(percentageValue) || percentageValue <= 0) {
      notify("برند و درصد معتبر را انتخاب کنید");
      return;
    }
    if (operation === "decrease" && percentageValue >= 100) {
      notify("درصد کاهش باید کمتر از ۱۰۰ باشد");
      return;
    }
    const operationLabel = operation === "increase" ? "افزایش" : "کاهش";
    const confirmed = window.confirm(
      `قیمت ${faNum(selectedBrand.productCount)} محصول برند «${selectedBrand.name}» ${operationLabel} ${percentageValue.toLocaleString("fa-IR")} درصدی داشته باشد؟ این تغییر گروهی است.`
    );
    if (!confirmed) return;

    setAdjusting(true);
    const result = await api.post<{ updatedCount: number }>(
      `/api/admin/brands/${selectedBrand.id}/price-adjustment`,
      { operation, percentage }
    );
    setAdjusting(false);
    if (result.ok && result.data) {
      notify(
        `قیمت ${faNum(result.data.updatedCount)} محصول با موفقیت تغییر کرد ✅`
      );
      setPercentage("");
    } else notify(result.error ?? "تغییر گروهی قیمت‌ها انجام نشد");
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-slate-800">مدیریت برندها</h1>
        <p className="mt-1 text-xs leading-6 text-slate-400">
          برندها مستقل از دسته‌بندی‌ها هستند و هر محصول حداکثر یک برند دارد.
        </p>
      </div>

      {message && (
        <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">
          {message}
        </p>
      )}

      <section
        ref={formSection}
        className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-5"
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <h2 className="font-bold text-slate-700">
            {editing ? `ویرایش «${editing.name}»` : "افزودن برند"}
          </h2>
          {editing && (
            <button
              type="button"
              onClick={resetForm}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              انصراف از ویرایش
            </button>
          )}
        </div>
        <form onSubmit={save} className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <label>
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              نام برند
            </span>
            <input
              required
              maxLength={100}
              value={form.name}
              onChange={(event) =>
                setForm((current) => ({ ...current, name: event.target.value }))
              }
              className={INPUT_CLASS}
              placeholder="مثلاً Bosch"
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              نامک انگلیسی
            </span>
            <input
              required
              dir="ltr"
              maxLength={100}
              pattern="[-a-zA-Z0-9_]+"
              value={form.slug}
              onChange={(event) =>
                setForm((current) => ({ ...current, slug: event.target.value }))
              }
              className={`${INPUT_CLASS} font-mono`}
              placeholder="bosch"
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              وب‌سایت (اختیاری)
            </span>
            <input
              type="url"
              dir="ltr"
              value={form.website}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  website: event.target.value,
                }))
              }
              className={INPUT_CLASS}
              placeholder="https://example.com"
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              {editing?.logo ? "جایگزینی نشان" : "نشان (اختیاری)"}
            </span>
            <input
              ref={fileInput}
              type="file"
              accept=".png,.svg,image/png,image/svg+xml"
              onChange={(event) => setLogo(event.target.files?.[0] ?? null)}
              className={`${INPUT_CLASS} file:ml-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-xs file:text-brand-700`}
            />
          </label>
          <label className="min-w-0 lg:col-span-2">
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              توضیحات (اختیاری)
            </span>
            <textarea
              rows={3}
              value={form.description}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              className={`${INPUT_CLASS} resize-none leading-7`}
            />
          </label>
          <div className="min-w-0 lg:col-span-2">
            <button
              disabled={saving}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white disabled:opacity-60"
            >
              {saving
                ? "در حال ذخیره..."
                : editing
                  ? "ذخیره تغییرات"
                  : "+ افزودن برند"}
            </button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-amber-100 bg-amber-50/50 p-5">
        <h2 className="font-bold text-slate-700">تغییر گروهی قیمت بر اساس برند</h2>
        <p className="mt-1 text-xs leading-6 text-slate-500">
          قیمت فروش و قیمت قبل همه محصولات برند انتخاب‌شده با گرد کردن به نزدیک‌ترین
          تومان تغییر می‌کند.
        </p>
        <form onSubmit={adjustPrices} className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-4">
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">برند</span>
            <select
              required
              value={selectedBrandId}
              onChange={(event) => setSelectedBrandId(event.target.value)}
              className={INPUT_CLASS}
            >
              <option value="">انتخاب برند</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name} ({faNum(brand.productCount)} محصول)
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">عملیات</span>
            <select
              value={operation}
              onChange={(event) =>
                setOperation(event.target.value as "increase" | "decrease")
              }
              className={INPUT_CLASS}
            >
              <option value="increase">افزایش قیمت</option>
              <option value="decrease">کاهش قیمت</option>
            </select>
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">درصد</span>
            <input
              required
              type="number"
              inputMode="decimal"
              min="0.01"
              max={operation === "decrease" ? "99.99" : "1000"}
              step="0.01"
              value={percentage}
              onChange={(event) => setPercentage(event.target.value)}
              className={`${INPUT_CLASS} font-num`}
              placeholder="10"
            />
          </label>
          <div className="flex items-end">
            <button
              disabled={adjusting}
              className="w-full rounded-xl bg-amber-500 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-amber-600 disabled:opacity-60"
            >
              {adjusting ? "در حال اعمال..." : "بررسی و اعمال تغییر"}
            </button>
          </div>
        </form>
      </section>

      <section className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">برند</th>
              <th className="px-3 py-3 font-medium">نامک</th>
              <th className="px-3 py-3 font-medium">محصولات</th>
              <th className="px-3 py-3 font-medium">نمایش</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={5} text="در حال بارگذاری..." />
            ) : brands.length === 0 ? (
              <EmptyRow colSpan={5} text="برندی ثبت نشده است" />
            ) : (
              brands.map((brand) => (
                <tr key={brand.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl bg-slate-50 ring-1 ring-slate-100">
                        {brand.logo ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={brand.logo}
                            alt=""
                            className="h-8 w-8 object-contain"
                          />
                        ) : (
                          <span aria-hidden="true">🏷️</span>
                        )}
                      </span>
                      <span className="text-xs font-medium text-slate-700">
                        {brand.name}
                      </span>
                    </div>
                  </td>
                  <td dir="ltr" className="px-3 py-3 text-right font-mono text-xs text-slate-500">
                    {brand.slug}
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500 font-num">
                    {faNum(brand.productCount)}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`rounded-lg px-2.5 py-1 text-[11px] ${
                        brand.isActive
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {brand.isActive ? "فعال" : "پنهان"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3 text-xs">
                      <button
                        type="button"
                        disabled={changingVisibility !== null}
                        onClick={() => toggleVisibility(brand)}
                        className="text-slate-500 hover:underline disabled:opacity-50"
                      >
                        {changingVisibility === brand.id
                          ? "در حال تغییر..."
                          : brand.isActive
                            ? "پنهان کردن"
                            : "نمایش دادن"}
                      </button>
                      <button
                        type="button"
                        onClick={() => startEditing(brand)}
                        className="text-brand-600 hover:underline"
                      >
                        ویرایش
                      </button>
                      {brand.logo && (
                        <button
                          type="button"
                          onClick={() => removeLogo(brand)}
                          className="text-amber-600 hover:underline"
                        >
                          حذف نشان
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => remove(brand)}
                        className="text-red-400 hover:text-red-600"
                      >
                        حذف
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
