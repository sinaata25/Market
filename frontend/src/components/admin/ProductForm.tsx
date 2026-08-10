"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/client-api";
import type { Category, Product } from "@/lib/products";

type FormState = {
  title: string;
  titleEn: string;
  categorySlugs: string[];
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
  categorySlugs: [],
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
  const editingExistingProduct = productId !== undefined;

  const [form, setForm] = useState<FormState>(EMPTY);
  const [categories, setCategories] = useState<Category[]>([]);
  const [images, setImages] = useState<ImageItem[]>([]);
  const [pendingImages, setPendingImages] = useState<File[]>([]);
  const [createdProductId, setCreatedProductId] = useState<number>();
  const [loading, setLoading] = useState(editingExistingProduct);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [changingVisibility, setChangingVisibility] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(
    null
  );
  const fileRef = useRef<HTMLInputElement>(null);
  const activeProductId = productId ?? createdProductId;
  const isEdit = activeProductId !== undefined;

  function set<K extends Exclude<keyof FormState, "categorySlugs">>(
    key: K,
    value: string
  ) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function toggleCategory(slug: string) {
    setForm((current) => ({
      ...current,
      categorySlugs: current.categorySlugs.includes(slug)
        ? current.categorySlugs.filter((item) => item !== slug)
        : [...current.categorySlugs, slug],
    }));
  }

  // دسته‌ها + در حالت ویرایش، خود محصول
  useEffect(() => {
    api.get<{ categories: Category[] }>("/api/admin/categories").then((res) => {
      if (res.ok && res.data) setCategories(res.data.categories);
    });
    if (editingExistingProduct) {
      api
        .get<{ product: AdminProduct }>(`/api/admin/products/${productId}`)
        .then((res) => {
          if (res.ok && res.data) {
            const p = res.data.product;
            setForm({
              title: p.title,
              titleEn: p.titleEn ?? "",
              categorySlugs:
                p.categorySlugs ?? (p.categorySlug ? [p.categorySlug] : []),
              price: String(p.price),
              oldPrice: p.oldPrice ? String(p.oldPrice) : "",
              stock: String(p.stock ?? 0),
              badge: p.badge ?? "",
              description: p.description ?? "",
              warranty: p.warranty ?? "",
            });
            setImages(p.imageItems ?? []);
            setIsActive(p.isActive !== false);
          }
          setLoading(false);
        });
    }
  }, [editingExistingProduct, productId]);

  async function sendImage(targetProductId: number, file: File) {
    const fd = new FormData();
    fd.append("file", file);
    return api.upload<{ product: AdminProduct }>(
      `/api/admin/products/${targetProductId}/image`,
      fd
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (form.categorySlugs.length === 0) {
      setMessage({ ok: false, text: "حداقل یک دسته‌بندی انتخاب کنید" });
      return;
    }
    setSaving(true);
    setMessage(null);

    const payload = {
      title: form.title.trim(),
      titleEn: form.titleEn.trim(),
      categorySlugs: form.categorySlugs,
      price: Number(form.price) || 0,
      oldPrice: form.oldPrice ? Number(form.oldPrice) : null,
      stock: Number(form.stock) || 0,
      badge: form.badge.trim(),
      description: form.description.trim(),
      warranty: form.warranty.trim(),
    };

    const res = isEdit
      ? await api.patch<{ product: Product }>(
          `/api/admin/products/${activeProductId}`,
          payload
        )
      : await api.post<{ product: Product }>("/api/admin/products", payload);

    if (!res.ok || !res.data) {
      setSaving(false);
      setMessage({ ok: false, text: res.error ?? "خطا در ذخیره" });
      return;
    }
    if (!isEdit) {
      const newProductId = res.data.product.id;
      setCreatedProductId(newProductId);
      setIsActive(res.data.product.isActive !== false);

      const failedFiles: File[] = [];
      let latestImages: ImageItem[] = [];
      for (const file of pendingImages) {
        const upload = await sendImage(newProductId, file);
        if (upload.ok && upload.data) {
          latestImages = upload.data.product.imageItems ?? latestImages;
        } else {
          failedFiles.push(file);
        }
      }

      setSaving(false);
      setImages(latestImages);
      setPendingImages(failedFiles);
      if (failedFiles.length > 0) {
        setMessage({
          ok: false,
          text: `محصول ایجاد شد، اما ${failedFiles.length.toLocaleString("fa-IR")} تصویر آپلود نشد. دوباره تلاش کنید.`,
        });
        return;
      }
      router.push(`/admin/products/${newProductId}`);
      return;
    }

    if (pendingImages.length > 0 && activeProductId !== undefined) {
      const failedFiles: File[] = [];
      let latestImages = images;
      for (const file of pendingImages) {
        const upload = await sendImage(activeProductId, file);
        if (upload.ok && upload.data) {
          latestImages = upload.data.product.imageItems ?? latestImages;
        } else {
          failedFiles.push(file);
        }
      }
      setImages(latestImages);
      setPendingImages(failedFiles);
      setSaving(false);
      if (failedFiles.length > 0) {
        setMessage({
          ok: false,
          text: `${failedFiles.length.toLocaleString("fa-IR")} تصویر همچنان آپلود نشد.`,
        });
        return;
      }
      router.push(`/admin/products/${activeProductId}`);
      return;
    }

    setSaving(false);
    setMessage({ ok: true, text: "تغییرات ذخیره شد ✅" });
  }

  async function uploadImage(file: File) {
    if (activeProductId === undefined) return;
    setUploading(true);
    setMessage(null);
    const res = await sendImage(activeProductId, file);
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
    if (activeProductId === undefined) return;
    if (!confirm("این تصویر حذف شود؟")) return;
    const res = await api.delete(
      `/api/admin/products/${activeProductId}/images/${img.id}`
    );
    if (res.ok) {
      setImages((prev) => prev.filter((i) => i.id !== img.id));
    } else {
      setMessage({ ok: false, text: res.error ?? "خطا در حذف تصویر" });
    }
  }

  async function toggleVisibility() {
    if (activeProductId === undefined || changingVisibility) return;
    setChangingVisibility(true);
    setMessage(null);
    const result = await api.patch<{ product: AdminProduct }>(
      `/api/admin/products/${activeProductId}/visibility`,
      { isActive: !isActive }
    );
    setChangingVisibility(false);
    if (result.ok && result.data) {
      const nextVisibility = result.data.product.isActive !== false;
      setIsActive(nextVisibility);
      setMessage({
        ok: true,
        text: nextVisibility
          ? "محصول در فروشگاه نمایش داده شد ✅"
          : "محصول از فروشگاه پنهان شد ✅",
      });
    } else {
      setMessage({
        ok: false,
        text: result.error ?? "تغییر وضعیت محصول انجام نشد",
      });
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
          {isEdit && (
            <div className="rounded-2xl border border-slate-100 bg-white p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-medium text-slate-600">
                    وضعیت نمایش محصول
                  </p>
                  <span
                    className={`mt-2 inline-flex rounded-lg px-2.5 py-1 text-[11px] font-medium ${
                      isActive
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {isActive ? "نمایش داده می‌شود" : "پنهان است"}
                  </span>
                </div>
                <button
                  type="button"
                  disabled={changingVisibility}
                  onClick={toggleVisibility}
                  className={`rounded-xl border px-3 py-2 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${
                    isActive
                      ? "border-slate-200 text-slate-600 hover:bg-slate-50"
                      : "border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                  }`}
                >
                  {changingVisibility
                    ? "در حال تغییر..."
                    : isActive
                      ? "پنهان کردن"
                      : "نمایش دادن"}
                </button>
              </div>
              <p className="mt-3 text-[11px] leading-5 text-slate-400">
                محصول پنهان در فروشگاه نمایش داده نمی‌شود، اما اطلاعات آن در پنل
                مدیریت باقی می‌ماند.
              </p>
            </div>
          )}

          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                دسته‌بندی *
              </label>
              <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3">
                {categories.length === 0 ? (
                  <p className="text-xs text-slate-400">
                    دسته‌بندی‌ای برای انتخاب وجود ندارد
                  </p>
                ) : (
                  categories.map((category) => (
                    <label
                      key={category.slug}
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-600 transition hover:bg-white"
                    >
                      <input
                        type="checkbox"
                        checked={form.categorySlugs.includes(category.slug)}
                        onChange={() => toggleCategory(category.slug)}
                        className="h-4 w-4 accent-brand-600"
                      />
                      <span>{category.title}</span>
                      {category.effectiveIsActive === false && (
                        <span className="mr-auto rounded bg-slate-200 px-1.5 py-0.5 text-[10px] text-slate-500">
                          {category.isActive === false
                            ? "پنهان"
                            : "پنهان توسط والد"}
                        </span>
                      )}
                    </label>
                  ))
                )}
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400">
                می‌توانید یک یا چند دسته‌بندی انتخاب کنید. اولین انتخاب، دسته‌بندی
                اصلی محصول است.
              </p>
              {form.categorySlugs.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {form.categorySlugs.map((slug, index) => {
                    const category = categories.find(
                      (item) => item.slug === slug
                    );
                    return (
                      <span
                        key={slug}
                        className={`rounded-lg px-2 py-1 text-[10px] ${
                          index === 0
                            ? "bg-brand-100 text-brand-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {category?.title ?? slug}
                        {index === 0 ? " (اصلی)" : ""}
                      </span>
                    );
                  })}
                </div>
              )}
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
                    {pendingImages.length > 0
                      ? `${pendingImages.length.toLocaleString("fa-IR")} تصویر آماده آپلود است`
                      : "هنوز تصویری ندارد"}
                  </p>
                )}
              </div>
              {pendingImages.length > 0 && (
                <ul className="mb-3 space-y-1.5 text-[11px] text-slate-500">
                  {pendingImages.map((file, index) => (
                    <li
                      key={`${file.name}-${file.lastModified}-${index}`}
                      className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-2.5 py-2"
                    >
                      <span className="truncate" dir="ltr">
                        {file.name}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setPendingImages((files) =>
                            files.filter((_, fileIndex) => fileIndex !== index)
                          )
                        }
                        className="shrink-0 text-red-500"
                      >
                        حذف
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <input
                ref={fileRef}
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => {
                  const files = Array.from(e.target.files ?? []);
                  if (files.length === 0) return;
                  if (isEdit) {
                    void (async () => {
                      for (const file of files) await uploadImage(file);
                    })();
                  } else {
                    setPendingImages((current) => [...current, ...files]);
                    e.target.value = "";
                  }
                }}
                className="hidden"
              />
              <button
                type="button"
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
                className="w-full rounded-xl border border-dashed border-slate-300 py-2.5 text-xs text-slate-500 transition hover:border-brand-400 hover:text-brand-700 disabled:opacity-50"
              >
                {uploading
                  ? "در حال آپلود..."
                  : isEdit
                    ? "⬆️ آپلود تصاویر (هر فایل حداکثر ۵MB)"
                    : "➕ انتخاب تصاویر (هر فایل حداکثر ۵MB)"}
              </button>
              {!isEdit && pendingImages.length > 0 && (
                <p className="mt-2 text-[11px] leading-5 text-slate-400">
                  تصاویر پس از ایجاد محصول به‌ترتیب آپلود می‌شوند.
                </p>
              )}
            </div>
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
          {saving
            ? !isEdit && pendingImages.length > 0
              ? "در حال ایجاد و آپلود تصاویر..."
              : "در حال ذخیره..."
            : isEdit
              ? "ذخیره تغییرات"
              : "ایجاد محصول"}
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
