"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { EmptyRow, faNum } from "@/components/admin/ui";
import { api } from "@/lib/client-api";
import type { Category } from "@/lib/products";

type AdminCategory = Category & {
  id: number;
  productCount: number;
};

type CategoryForm = {
  title: string;
  slug: string;
  subcategories: string;
};

const EMPTY_FORM: CategoryForm = {
  title: "",
  slug: "",
  subcategories: "",
};

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";

export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [form, setForm] = useState<CategoryForm>(EMPTY_FORM);
  const [editing, setEditing] = useState<AdminCategory | null>(null);
  const [icon, setIcon] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const formSection = useRef<HTMLElement>(null);

  const notify = useCallback((text: string) => {
    setMessage(text);
    window.setTimeout(() => setMessage(""), 5000);
  }, []);

  const load = useCallback(async () => {
    const result = await api.get<{ categories: AdminCategory[] }>(
      "/api/admin/categories"
    );
    if (result.ok) {
      setCategories(result.data?.categories ?? []);
    } else {
      notify(result.error ?? "دریافت دسته‌بندی‌ها انجام نشد");
    }
    setLoading(false);
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  function resetForm() {
    setForm(EMPTY_FORM);
    setEditing(null);
    setIcon(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function startEditing(category: AdminCategory) {
    setEditing(category);
    setForm({
      title: category.title,
      slug: category.slug,
      subcategories: category.sub.join("\n"),
    });
    setIcon(null);
    if (fileInput.current) fileInput.current.value = "";
    formSection.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);

    const payload = {
      title: form.title.trim(),
      slug: form.slug.trim(),
      sub: form.subcategories
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean),
    };
    const result = editing
      ? await api.patch<{ category: AdminCategory }>(
          `/api/admin/categories/${editing.id}`,
          payload
        )
      : await api.post<{ category: AdminCategory }>(
          "/api/admin/categories",
          payload
        );

    if (!result.ok || !result.data) {
      notify(result.error ?? "ذخیره دسته‌بندی انجام نشد");
      setSaving(false);
      return;
    }

    if (icon) {
      const iconForm = new FormData();
      iconForm.append("file", icon);
      const upload = await api.upload<{ category: AdminCategory }>(
        `/api/admin/categories/${result.data.category.id}/icon`,
        iconForm
      );
      if (!upload.ok) {
        notify(
          `دسته‌بندی ذخیره شد، اما آیکن بارگذاری نشد: ${upload.error ?? "خطای نامشخص"}`
        );
        resetForm();
        setSaving(false);
        await load();
        return;
      }
    }

    notify(editing ? "دسته‌بندی ویرایش شد ✅" : "دسته‌بندی افزوده شد ✅");
    resetForm();
    setSaving(false);
    await load();
  }

  async function remove(category: AdminCategory) {
    const warning = category.productCount
      ? `این دسته‌بندی ${faNum(category.productCount)} محصول دارد و قابل حذف نیست.`
      : `دسته‌بندی «${category.title}» حذف شود؟ این کار قابل بازگشت نیست.`;
    if (category.productCount) {
      notify(warning);
      return;
    }
    if (!window.confirm(warning)) return;

    const result = await api.delete(`/api/admin/categories/${category.id}`);
    if (result.ok) {
      if (editing?.id === category.id) resetForm();
      notify("دسته‌بندی حذف شد ✅");
      await load();
    } else {
      notify(result.error ?? "حذف دسته‌بندی انجام نشد");
    }
  }

  async function removeIcon(category: AdminCategory) {
    if (!window.confirm(`آیکن دسته‌بندی «${category.title}» حذف شود؟`)) return;
    const result = await api.delete(
      `/api/admin/categories/${category.id}/icon`
    );
    if (result.ok) {
      notify("آیکن حذف شد ✅");
      await load();
    } else {
      notify(result.error ?? "حذف آیکن انجام نشد");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-slate-800">مدیریت دسته‌بندی‌ها</h1>
        <p className="mt-1 text-xs leading-6 text-slate-400">
          دسته‌بندی‌های فروشگاه، زیردسته‌ها و آیکن هر دسته را مدیریت کنید.
        </p>
      </div>

      {message && (
        <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">
          {message}
        </p>
      )}

      <section
        ref={formSection}
        className="scroll-mt-24 rounded-2xl border border-slate-100 bg-white p-5"
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="font-bold text-slate-700">
            {editing ? `ویرایش «${editing.title}»` : "افزودن دسته‌بندی"}
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

        <form onSubmit={save} className="grid gap-4 lg:grid-cols-2">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              عنوان دسته‌بندی
            </span>
            <input
              required
              maxLength={100}
              value={form.title}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  title: event.target.value,
                }))
              }
              className={INPUT_CLASS}
              placeholder="مثلاً ابزار باغبانی"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              نامک انگلیسی
            </span>
            <input
              required
              dir="ltr"
              maxLength={50}
              pattern="[-a-zA-Z0-9_]+"
              value={form.slug}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  slug: event.target.value,
                }))
              }
              className={`${INPUT_CLASS} font-mono`}
              placeholder="garden-tools"
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              زیردسته‌ها
            </span>
            <textarea
              rows={5}
              value={form.subcategories}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  subcategories: event.target.value,
                }))
              }
              className={`${INPUT_CLASS} resize-y`}
              placeholder={"هر زیردسته را در یک خط وارد کنید\nبیل و کلنگ\nقیچی باغبانی"}
            />
          </label>

          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              {editing?.icon ? "جایگزینی آیکن" : "آیکن (اختیاری)"}
            </span>
            <input
              ref={fileInput}
              type="file"
              accept=".png,.svg,image/png,image/svg+xml"
              onChange={(event) => setIcon(event.target.files?.[0] ?? null)}
              className={`${INPUT_CLASS} file:ml-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-1.5 file:text-xs file:text-brand-700`}
            />
            <p className="mt-1.5 text-[11px] text-slate-400">
              فایل PNG یا SVG امن، حداکثر ۵ مگابایت
            </p>
          </label>

          <div className="lg:col-span-2">
            <button
              disabled={saving}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving
                ? "در حال ذخیره..."
                : editing
                  ? "ذخیره تغییرات"
                  : "+ افزودن دسته‌بندی"}
            </button>
          </div>
        </form>
      </section>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[680px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">دسته‌بندی</th>
              <th className="px-3 py-3 font-medium">نامک</th>
              <th className="px-3 py-3 font-medium">زیردسته‌ها</th>
              <th className="px-3 py-3 font-medium">محصولات</th>
              <th className="px-5 py-3 font-medium">عملیات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={5} text="در حال بارگذاری..." />
            ) : categories.length === 0 ? (
              <EmptyRow colSpan={5} text="دسته‌بندی‌ای وجود ندارد" />
            ) : (
              categories.map((category) => (
                <tr key={category.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl bg-brand-50 text-lg">
                        {category.icon ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={category.icon}
                            alt=""
                            className="h-6 w-6 object-contain"
                          />
                        ) : (
                          "🗂️"
                        )}
                      </span>
                      <span className="text-xs font-medium text-slate-700">
                        {category.title}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-400" dir="ltr">
                    {category.slug}
                  </td>
                  <td className="max-w-[240px] px-3 py-3 text-xs text-slate-500">
                    <p className="line-clamp-2">
                      {category.sub.length ? category.sub.join("، ") : "—"}
                    </p>
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-500 font-num">
                    {faNum(category.productCount)}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3 text-xs">
                      <button
                        type="button"
                        onClick={() => startEditing(category)}
                        className="text-brand-600 hover:underline"
                      >
                        ویرایش
                      </button>
                      {category.icon && (
                        <button
                          type="button"
                          onClick={() => removeIcon(category)}
                          className="text-amber-600 hover:underline"
                        >
                          حذف آیکن
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => remove(category)}
                        className="text-red-400 hover:text-red-600"
                        title={
                          category.productCount
                            ? "ابتدا محصولات این دسته‌بندی را منتقل یا حذف کنید"
                            : undefined
                        }
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
      </div>
    </div>
  );
}
