"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/client-api";
import type { Category, Product } from "@/lib/products";

type FormState = {
  title: string;
  titleEn: string;
  categorySlug: string;
  price: string;
  oldPrice: string;
  stock: string;
  badge: string;
  description: string;
  warranty: string;
};

const EMPTY: FormState = {
  title: "",
  titleEn: "",
  categorySlug: "",
  price: "",
  oldPrice: "",
  stock: "10",
  badge: "",
  description: "",
  warranty: "",
};

function inputCls(hasError = false) {
  return `w-full rounded-xl border bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:bg-white ${
    hasError ? "border-red-300" : "border-slate-200 focus:border-brand-400"
  }`;
}

type ImageItem = { id: number; url: string };
type AdminProduct = Product & { imageItems?: ImageItem[] };

export default function ProductForm({ productId }: { productId?: number }) {
  const router = useRouter();
  const isEdit = productId !== undefined;

  const [form, setForm] = useState<FormState>(EMPTY);
  const [categories, setCategories] = useState<Category[]>([]);
  const [images, setImages] = useState<ImageItem[]>([]);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(
    null
  );
  const fileRef = useRef<HTMLInputElement>(null);

  function set<K extends keyof FormState>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  // دسته‌ها + در حالت ویرایش، خود محصول
  useEffect(() => {
    api.get<{ categories: Category[] }>("/api/categories").then((res) => {
      if (res.ok && res.data) setCategories(res.data.categories);
    });
    if (isEdit) {
      api
        .get<{ product: AdminProduct }>(`/api/admin/products/${productId}`)
        .then((res) => {
          if (res.ok && res.data) {
            const p = res.data.product;
            setForm({
              title: p.title,
              titleEn: p.titleEn ?? "",
              categorySlug: p.categorySlug ?? "",
              price: String(p.price),
              oldPrice: p.oldPrice ? String(p.oldPrice) : "",
              stock: String(p.stock ?? 0),
              badge: p.badge ?? "",
              description: p.description ?? "",
              warranty: p.warranty ?? "",
            });
            setImages(p.imageItems ?? []);
          }
          setLoading(false);
        });
    }
  }, [isEdit, productId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    const payload = {
      title: form.title.trim(),
      titleEn: form.titleEn.trim(),
      categorySlug: form.categorySlug,
      price: Number(form.price) || 0,
      oldPrice: form.oldPrice ? Number(form.oldPrice) : null,
      stock: Number(form.stock) || 0,
      badge: form.badge.trim(),
      description: form.description.trim(),
      warranty: form.warranty.trim(),
    };

    const res = isEdit
      ? await api.patch<{ product: Product }>(
          `/api/admin/products/${productId}`,
          payload
        )
      : await api.post<{ product: Product }>("/api/admin/products", payload);

    setSaving(false);
    if (!res.ok || !res.data) {
      setMessage({ ok: false, text: res.error ?? "خطا در ذخیره" });
      return;
    }
    if (!isEdit) {
      // بعد از ساخت، برو به صفحه ویرایش برای آپلود عکس
      router.push(`/admin/products/${res.data.product.id}`);
      return;
    }
    setMessage({ ok: true, text: "تغییرات ذخیره شد ✅" });
  }

  async function uploadImage(file: File) {
    setUploading(true);
    setMessage(null);
    const fd = new FormData();
    fd.append("file", file);
    const res = await api.upload<{ product: AdminProduct }>(
      `/api/admin/products/${productId}/image`,
      fd
    );
    setUploading(false);
    if (res.ok && res.data) {
      setImages(res.data.product.imageItems ?? []);
      setMessage({ ok: true, text: "تصویر آپلود شد ✅" });
    } else {
      setMessage({ ok: false, text: res.error ?? "خطا در آپلود" });
    }
    if (fileRef.current) fileRef.current.value = "";
  }

  async function removeImage(img: ImageItem) {
    if (!confirm("این تصویر حذف شود؟")) return;
    const res = await api.delete(
      `/api/admin/products/${productId}/images/${img.id}`
    );
    if (res.ok) {
      setImages((prev) => prev.filter((i) => i.id !== img.id));
    } else {
      setMessage({ ok: false, text: res.error ?? "خطا در حذف تصویر" });
    }
  }

  if (loading) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-3">
        {/* ستون اصلی */}
        <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5 lg:col-span-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              عنوان محصول *
            </label>
            <input
              required
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              className={inputCls()}
              placeholder="مثلا: اره موتوری حرفه‌ای ۵۲ سی‌سی"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              عنوان انگلیسی
            </label>
            <input
              dir="ltr"
              value={form.titleEn}
              onChange={(e) => set("titleEn", e.target.value)}
              className={inputCls()}
              placeholder="Professional Chainsaw 52cc"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              توضیحات
            </label>
            <textarea
              rows={4}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              className={`${inputCls()} resize-none leading-7`}
              placeholder="معرفی کامل محصول..."
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                گارانتی
              </label>
              <input
                value={form.warranty}
                onChange={(e) => set("warranty", e.target.value)}
                className={inputCls()}
                placeholder="۱۸ ماه گارانتی شرکتی"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                برچسب
              </label>
              <input
                value={form.badge}
                onChange={(e) => set("badge", e.target.value)}
                className={inputCls()}
                placeholder="پرفروش / تخفیف ویژه"
              />
            </div>
          </div>
        </div>

        {/* ستون کناری */}
        <div className="space-y-4">
          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                دسته‌بندی *
              </label>
              <select
                required
                value={form.categorySlug}
                onChange={(e) => set("categorySlug", e.target.value)}
                className={inputCls()}
              >
                <option value="">انتخاب کنید...</option>
                {categories.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.title}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  قیمت فروش *
                </label>
                <input
                  required
                  type="number"
                  min={0}
                  value={form.price}
                  onChange={(e) => set("price", e.target.value)}
                  className={`${inputCls()} font-num`}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  قیمت قبل (تخفیف)
                </label>
                <input
                  type="number"
                  min={0}
                  value={form.oldPrice}
                  onChange={(e) => set("oldPrice", e.target.value)}
                  className={`${inputCls()} font-num`}
                  placeholder="اختیاری"
                />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                موجودی *
              </label>
              <input
                required
                type="number"
                min={0}
                value={form.stock}
                onChange={(e) => set("stock", e.target.value)}
                className={`${inputCls()} font-num`}
              />
            </div>
          </div>

          {/* تصاویر — فقط در ویرایش */}
          {isEdit && (
            <div className="rounded-2xl border border-slate-100 bg-white p-5">
              <label className="mb-3 block text-xs font-medium text-slate-600">
                تصاویر محصول
              </label>
              <div className="mb-3 grid grid-cols-3 gap-2">
                {images.map((img) => (
                  <div
                    key={img.id}
                    className="group relative aspect-square overflow-hidden rounded-xl border border-slate-100"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={img.url}
                      alt=""
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => removeImage(img)}
                      className="absolute inset-0 hidden place-items-center bg-black/50 text-lg text-white group-hover:grid"
                      title="حذف"
                    >
                      🗑
                    </button>
                  </div>
                ))}
                {images.length === 0 && (
                  <p className="col-span-3 py-4 text-center text-[11px] text-slate-400">
                    هنوز تصویری ندارد
                  </p>
                )}
              </div>
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) uploadImage(f);
                }}
                className="hidden"
              />
              <button
                type="button"
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
                className="w-full rounded-xl border border-dashed border-slate-300 py-2.5 text-xs text-slate-500 transition hover:border-brand-400 hover:text-brand-700 disabled:opacity-50"
              >
                {uploading ? "در حال آپلود..." : "⬆️ آپلود تصویر (حداکثر ۵MB)"}
              </button>
            </div>
          )}
        </div>
      </div>

      {message && (
        <p
          className={`rounded-xl px-4 py-3 text-xs ${
            message.ok
              ? "bg-emerald-50 text-emerald-700"
              : "bg-red-50 text-red-500"
          }`}
        >
          {message.text}
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="rounded-xl bg-brand-600 px-8 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {saving ? "در حال ذخیره..." : isEdit ? "ذخیره تغییرات" : "ایجاد محصول"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/admin/products")}
          className="rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm text-slate-600 transition hover:border-slate-300"
        >
          بازگشت
        </button>
      </div>
    </form>
  );
}
