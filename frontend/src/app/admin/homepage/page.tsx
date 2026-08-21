"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/client-api";
import type { Brand, Category } from "@/lib/products";

type SectionType =
  | "banner"
  | "categories"
  | "brands"
  | "best_sellers"
  | "discounted_products"
  | "new_products"
  | "product_collection"
  | "recently_viewed";

type Banner = {
  id: number;
  title: string | null;
  subtitle: string | null;
  image: string | null;
  theme: "brand" | "secondary" | "accent";
  linkUrl: string | null;
  linkLabel: string | null;
  isActive: boolean;
  sectionCount: number;
};

type Section = {
  id: number;
  sectionType: SectionType;
  title: string | null;
  resolvedTitle: string | null;
  position: number;
  isActive: boolean;
  banner: Banner | null;
  category: { slug: string; title: string } | null;
  brand: Brand | null;
  sort: string | null;
  limit: number | null;
  resolvedLimit: number;
};

type SectionForm = {
  sectionType: SectionType;
  title: string;
  isActive: boolean;
  bannerId: string;
  categorySlug: string;
  brandSlug: string;
  sort: string;
  limit: string;
};

type BannerForm = {
  title: string;
  subtitle: string;
  theme: Banner["theme"];
  linkUrl: string;
  linkLabel: string;
  isActive: boolean;
};

const SECTION_TYPES: { value: SectionType; label: string }[] = [
  { value: "banner", label: "بنر" },
  { value: "categories", label: "دسته‌بندی‌ها" },
  { value: "brands", label: "برندها" },
  { value: "best_sellers", label: "پرفروش‌ترین‌ها" },
  { value: "discounted_products", label: "تخفیف‌های ویژه" },
  { value: "new_products", label: "جدیدترین محصولات" },
  { value: "product_collection", label: "مجموعه محصولات سفارشی" },
  { value: "recently_viewed", label: "محصولات اخیراً مشاهده‌شده" },
];

const SECTION_LABELS = Object.fromEntries(
  SECTION_TYPES.map((item) => [item.value, item.label])
) as Record<SectionType, string>;

const EMPTY_SECTION: SectionForm = {
  sectionType: "categories",
  title: "",
  isActive: true,
  bannerId: "",
  categorySlug: "",
  brandSlug: "",
  sort: "newest",
  limit: "",
};

const EMPTY_BANNER: BannerForm = {
  title: "",
  subtitle: "",
  theme: "brand",
  linkUrl: "",
  linkLabel: "",
  isActive: true,
};

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white disabled:opacity-60";

function sectionForm(section: Section): SectionForm {
  return {
    sectionType: section.sectionType,
    title: section.title ?? "",
    isActive: section.isActive,
    bannerId: section.banner ? String(section.banner.id) : "",
    categorySlug: section.category?.slug ?? "",
    brandSlug: section.brand?.slug ?? "",
    sort: section.sort ?? "newest",
    limit: section.limit ? String(section.limit) : "",
  };
}

function bannerForm(banner: Banner): BannerForm {
  return {
    title: banner.title ?? "",
    subtitle: banner.subtitle ?? "",
    theme: banner.theme,
    linkUrl: banner.linkUrl ?? "",
    linkLabel: banner.linkLabel ?? "",
    isActive: banner.isActive,
  };
}

export default function AdminHomepagePage() {
  const [sections, setSections] = useState<Section[]>([]);
  const [banners, setBanners] = useState<Banner[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [sectionValues, setSectionValues] = useState(EMPTY_SECTION);
  const [bannerValues, setBannerValues] = useState(EMPTY_BANNER);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [editingBanner, setEditingBanner] = useState<Banner | null>(null);
  const [bannerImage, setBannerImage] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const sectionEditor = useRef<HTMLElement>(null);
  const bannerEditor = useRef<HTMLElement>(null);

  const notify = useCallback((text: string) => {
    setMessage(text);
    window.setTimeout(() => setMessage(""), 5000);
  }, []);

  const load = useCallback(async () => {
    const [sectionResult, bannerResult, categoryResult, brandResult] =
      await Promise.all([
        api.get<{ sections: Section[] }>("/api/admin/home/sections"),
        api.get<{ banners: Banner[] }>("/api/admin/home/banners"),
        api.get<{ categories: Category[] }>("/api/categories"),
        api.get<{ brands: Brand[] }>("/api/brands"),
      ]);
    if (sectionResult.ok) setSections(sectionResult.data?.sections ?? []);
    if (bannerResult.ok) setBanners(bannerResult.data?.banners ?? []);
    if (categoryResult.ok) setCategories(categoryResult.data?.categories ?? []);
    if (brandResult.ok) setBrands(brandResult.data?.brands ?? []);
    const failure = [sectionResult, bannerResult, categoryResult, brandResult].find(
      (result) => !result.ok
    );
    if (failure) notify(failure.error ?? "دریافت اطلاعات صفحه اصلی انجام نشد");
    setLoading(false);
  }, [notify]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [load]);

  function resetSection() {
    setEditingSection(null);
    setSectionValues(EMPTY_SECTION);
  }

  function resetBanner() {
    setEditingBanner(null);
    setBannerValues(EMPTY_BANNER);
    setBannerImage(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function editSection(section: Section) {
    setEditingSection(section);
    setSectionValues(sectionForm(section));
    sectionEditor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function editBanner(banner: Banner) {
    setEditingBanner(banner);
    setBannerValues(bannerForm(banner));
    setBannerImage(null);
    if (fileInput.current) fileInput.current.value = "";
    bannerEditor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveSection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const type = sectionValues.sectionType;
    const payload: Record<string, unknown> = {
      title: sectionValues.title.trim(),
      isActive: sectionValues.isActive,
    };
    if (!editingSection) payload.sectionType = type;
    if (type === "banner") {
      if (!sectionValues.bannerId) {
        notify("برای بخش بنر، یک بنر انتخاب کنید");
        return;
      }
      payload.bannerId = Number(sectionValues.bannerId);
    }
    if (type !== "banner") {
      payload.limit = sectionValues.limit ? Number(sectionValues.limit) : null;
    }
    if (type === "product_collection") {
      payload.categorySlug = sectionValues.categorySlug || null;
      payload.brandSlug = sectionValues.brandSlug || null;
      payload.sort = sectionValues.sort;
    }

    setBusy(true);
    const result = editingSection
      ? await api.patch<{ section: Section }>(
          `/api/admin/home/sections/${editingSection.id}`,
          payload
        )
      : await api.post<{ section: Section }>("/api/admin/home/sections", payload);
    setBusy(false);
    if (!result.ok) {
      notify(result.error ?? "ذخیره بخش انجام نشد");
      return;
    }
    notify(editingSection ? "بخش ویرایش شد ✅" : "بخش به انتهای صفحه افزوده شد ✅");
    resetSection();
    await load();
  }

  async function toggleSection(section: Section) {
    if (busy) return;
    setBusy(true);
    const result = await api.patch(`/api/admin/home/sections/${section.id}`, {
      isActive: !section.isActive,
    });
    setBusy(false);
    if (!result.ok) notify(result.error ?? "تغییر وضعیت انجام نشد");
    else await load();
  }

  async function moveSection(section: Section, direction: "up" | "down") {
    if (busy) return;
    setBusy(true);
    const result = await api.post<{ sections: Section[] }>(
      `/api/admin/home/sections/${section.id}/move`,
      { direction }
    );
    setBusy(false);
    if (!result.ok) notify(result.error ?? "تغییر ترتیب انجام نشد");
    else setSections(result.data?.sections ?? []);
  }

  async function removeSection(section: Section) {
    if (!window.confirm(`بخش «${section.resolvedTitle ?? SECTION_LABELS[section.sectionType]}» حذف شود؟`)) return;
    setBusy(true);
    const result = await api.delete(`/api/admin/home/sections/${section.id}`);
    setBusy(false);
    if (!result.ok) notify(result.error ?? "حذف بخش انجام نشد");
    else {
      if (editingSection?.id === section.id) resetSection();
      await load();
    }
  }

  async function saveBanner(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    const payload = {
      title: bannerValues.title.trim(),
      subtitle: bannerValues.subtitle.trim(),
      theme: bannerValues.theme,
      linkUrl: bannerValues.linkUrl.trim(),
      linkLabel: bannerValues.linkLabel.trim(),
      isActive: bannerValues.isActive,
    };
    const result = editingBanner
      ? await api.patch<{ banner: Banner }>(
          `/api/admin/home/banners/${editingBanner.id}`,
          payload
        )
      : await api.post<{ banner: Banner }>("/api/admin/home/banners", payload);
    if (!result.ok || !result.data) {
      setBusy(false);
      notify(result.error ?? "ذخیره بنر انجام نشد");
      return;
    }
    if (bannerImage) {
      const form = new FormData();
      form.append("file", bannerImage);
      const upload = await api.upload<{ banner: Banner }>(
        `/api/admin/home/banners/${result.data.banner.id}/image`,
        form
      );
      if (!upload.ok) {
        setBusy(false);
        notify(`بنر ذخیره شد، اما تصویر بارگذاری نشد: ${upload.error ?? "خطای نامشخص"}`);
        await load();
        return;
      }
    }
    setBusy(false);
    notify(editingBanner ? "بنر ویرایش شد ✅" : "بنر افزوده شد ✅");
    resetBanner();
    await load();
  }

  async function removeBanner(banner: Banner) {
    const usage = banner.sectionCount
      ? ` این بنر در ${banner.sectionCount.toLocaleString("fa-IR")} بخش استفاده شده و آن بخش‌ها پس از حذف نمایش داده نمی‌شوند.`
      : "";
    if (!window.confirm(`بنر «${banner.title ?? `#${banner.id}`}» حذف شود؟${usage}`)) return;
    setBusy(true);
    const result = await api.delete(`/api/admin/home/banners/${banner.id}`);
    setBusy(false);
    if (!result.ok) notify(result.error ?? "حذف بنر انجام نشد");
    else {
      if (editingBanner?.id === banner.id) resetBanner();
      await load();
    }
  }

  const type = sectionValues.sectionType;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-bold text-slate-800">ساختار صفحه اصلی</h1>
        <p className="mt-1 text-xs leading-6 text-slate-400">
          بخش‌ها از بالا به پایین مطابق همین فهرست در فروشگاه نمایش داده می‌شوند.
        </p>
      </div>

      {message && (
        <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">{message}</p>
      )}

      <section className="overflow-hidden rounded-2xl border border-slate-100 bg-white">
        <div className="border-b border-slate-100 px-5 py-4 font-bold text-slate-700">
          ترتیب فعلی
        </div>
        {loading ? (
          <p className="p-8 text-center text-sm text-slate-400">در حال دریافت...</p>
        ) : sections.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">هنوز بخشی افزوده نشده است.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {sections.map((section, index) => (
              <div key={section.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">
                  {(index + 1).toLocaleString("fa-IR")}
                </span>
                <div className="min-w-44 flex-1">
                  <p className="text-sm font-bold text-slate-700">
                    {section.resolvedTitle ?? SECTION_LABELS[section.sectionType]}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {SECTION_LABELS[section.sectionType]}
                    {section.limit ? ` · حداکثر ${section.limit.toLocaleString("fa-IR")}` : ""}
                  </p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] ${section.isActive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {section.isActive ? "فعال" : "غیرفعال"}
                </span>
                <div className="flex items-center gap-1">
                  <button type="button" disabled={busy || index === 0} onClick={() => moveSection(section, "up")} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs disabled:opacity-30" title="انتقال به بالا">↑</button>
                  <button type="button" disabled={busy || index === sections.length - 1} onClick={() => moveSection(section, "down")} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs disabled:opacity-30" title="انتقال به پایین">↓</button>
                  <button type="button" disabled={busy} onClick={() => toggleSection(section)} className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs text-slate-600">{section.isActive ? "غیرفعال" : "فعال"}</button>
                  <button type="button" onClick={() => editSection(section)} className="rounded-lg border border-brand-200 px-2.5 py-1.5 text-xs text-brand-700">ویرایش</button>
                  <button type="button" disabled={busy} onClick={() => removeSection(section)} className="rounded-lg border border-red-100 px-2.5 py-1.5 text-xs text-red-600">حذف</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section ref={sectionEditor} className="scroll-mt-24 rounded-2xl border border-slate-100 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-bold text-slate-700">{editingSection ? "ویرایش بخش" : "افزودن بخش"}</h2>
          {editingSection && <button type="button" onClick={resetSection} className="text-xs text-slate-400">انصراف</button>}
        </div>
        <form onSubmit={saveSection} className="grid gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">نوع بخش</span>
            <select disabled={Boolean(editingSection)} value={type} onChange={(event) => setSectionValues((current) => ({ ...current, sectionType: event.target.value as SectionType }))} className={INPUT_CLASS}>
              {SECTION_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">عنوان سفارشی (اختیاری)</span>
            <input value={sectionValues.title} onChange={(event) => setSectionValues((current) => ({ ...current, title: event.target.value }))} className={INPUT_CLASS} maxLength={150} placeholder="خالی = عنوان پیش‌فرض" />
          </label>
          {type === "banner" && (
            <label className="md:col-span-2">
              <span className="mb-1.5 block text-xs text-slate-600">بنر</span>
              <select required value={sectionValues.bannerId} onChange={(event) => setSectionValues((current) => ({ ...current, bannerId: event.target.value }))} className={INPUT_CLASS}>
                <option value="">انتخاب کنید</option>
                {banners.map((banner) => <option key={banner.id} value={banner.id}>{banner.title ?? `بنر #${banner.id}`}{banner.isActive ? "" : " (غیرفعال)"}</option>)}
              </select>
            </label>
          )}
          {type !== "banner" && (
            <label>
              <span className="mb-1.5 block text-xs text-slate-600">حداکثر تعداد (۱ تا ۲۴)</span>
              <input type="number" min={1} max={24} value={sectionValues.limit} onChange={(event) => setSectionValues((current) => ({ ...current, limit: event.target.value }))} className={INPUT_CLASS} placeholder="پیش‌فرض" />
            </label>
          )}
          {type === "product_collection" && (
            <>
              <label>
                <span className="mb-1.5 block text-xs text-slate-600">دسته‌بندی (اختیاری)</span>
                <select value={sectionValues.categorySlug} onChange={(event) => setSectionValues((current) => ({ ...current, categorySlug: event.target.value }))} className={INPUT_CLASS}><option value="">همه دسته‌بندی‌ها</option>{categories.map((category) => <option key={category.slug} value={category.slug}>{category.title}</option>)}</select>
              </label>
              <label>
                <span className="mb-1.5 block text-xs text-slate-600">برند (اختیاری)</span>
                <select value={sectionValues.brandSlug} onChange={(event) => setSectionValues((current) => ({ ...current, brandSlug: event.target.value }))} className={INPUT_CLASS}><option value="">همه برندها</option>{brands.map((brand) => <option key={brand.slug} value={brand.slug}>{brand.name}</option>)}</select>
              </label>
              <label>
                <span className="mb-1.5 block text-xs text-slate-600">مرتب‌سازی محصولات</span>
                <select value={sectionValues.sort} onChange={(event) => setSectionValues((current) => ({ ...current, sort: event.target.value }))} className={INPUT_CLASS}><option value="newest">جدیدترین</option><option value="cheapest">ارزان‌ترین</option><option value="expensive">گران‌ترین</option><option value="popular">محبوب‌ترین</option><option value="featured">ترتیب منتخب مدیر</option></select>
              </label>
            </>
          )}
          <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-600">
            <input type="checkbox" checked={sectionValues.isActive} onChange={(event) => setSectionValues((current) => ({ ...current, isActive: event.target.checked }))} />
            بخش فعال باشد
          </label>
          <div className="md:col-span-2">
            <button disabled={busy} className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">{busy ? "در حال ذخیره..." : editingSection ? "ذخیره تغییرات" : "افزودن به انتهای صفحه"}</button>
          </div>
        </form>
      </section>

      <section ref={bannerEditor} className="scroll-mt-24 rounded-2xl border border-slate-100 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div><h2 className="font-bold text-slate-700">{editingBanner ? "ویرایش بنر" : "ساخت بنر"}</h2><p className="mt-1 text-[11px] text-slate-400">یک بنر را می‌توان در چند جای صفحه اصلی استفاده کرد.</p></div>
          {editingBanner && <button type="button" onClick={resetBanner} className="text-xs text-slate-400">انصراف</button>}
        </div>
        <form onSubmit={saveBanner} className="grid gap-4 md:grid-cols-2">
          <label><span className="mb-1.5 block text-xs text-slate-600">عنوان</span><input value={bannerValues.title} onChange={(event) => setBannerValues((current) => ({ ...current, title: event.target.value }))} className={INPUT_CLASS} maxLength={150} /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">زیرعنوان</span><input value={bannerValues.subtitle} onChange={(event) => setBannerValues((current) => ({ ...current, subtitle: event.target.value }))} className={INPUT_CLASS} maxLength={300} /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">لینک مقصد</span><input dir="ltr" value={bannerValues.linkUrl} onChange={(event) => setBannerValues((current) => ({ ...current, linkUrl: event.target.value }))} className={INPUT_CLASS} placeholder="/category/..." /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">متن دکمه</span><input value={bannerValues.linkLabel} onChange={(event) => setBannerValues((current) => ({ ...current, linkLabel: event.target.value }))} className={INPUT_CLASS} maxLength={60} /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">رنگ زمینه</span><select value={bannerValues.theme} onChange={(event) => setBannerValues((current) => ({ ...current, theme: event.target.value as Banner["theme"] }))} className={INPUT_CLASS}><option value="brand">سبز برند</option><option value="secondary">آبی</option><option value="accent">طلایی</option></select></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">تصویر (اختیاری، حداکثر ۵ مگابایت)</span><input ref={fileInput} type="file" accept="image/*" onChange={(event) => setBannerImage(event.target.files?.[0] ?? null)} className={INPUT_CLASS} /></label>
          <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={bannerValues.isActive} onChange={(event) => setBannerValues((current) => ({ ...current, isActive: event.target.checked }))} />بنر فعال باشد</label>
          <div className="md:col-span-2"><button disabled={busy} className="rounded-xl bg-secondary-900 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">{busy ? "در حال ذخیره..." : editingBanner ? "ذخیره بنر" : "ساخت بنر"}</button></div>
        </form>
      </section>

      <section className="rounded-2xl border border-slate-100 bg-white p-5">
        <h2 className="mb-4 font-bold text-slate-700">بنرهای موجود</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {banners.map((banner) => (
            <article key={banner.id} className="flex min-w-0 gap-3 rounded-xl border border-slate-100 p-3">
              {banner.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={banner.image} alt="" className="h-16 w-24 shrink-0 rounded-lg object-cover" />
              ) : <span className="grid h-16 w-24 shrink-0 place-items-center rounded-lg bg-brand-50 text-2xl">🚜</span>}
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold text-slate-700">{banner.title ?? `بنر #${banner.id}`}</p><p className="mt-1 text-[11px] text-slate-400">استفاده در {banner.sectionCount.toLocaleString("fa-IR")} بخش · {banner.isActive ? "فعال" : "غیرفعال"}</p><div className="mt-2 flex gap-2"><button type="button" onClick={() => editBanner(banner)} className="text-xs text-brand-700">ویرایش</button><button type="button" disabled={busy} onClick={() => removeBanner(banner)} className="text-xs text-red-600">حذف</button></div></div>
            </article>
          ))}
          {!banners.length && <p className="text-sm text-slate-400">هنوز بنری ساخته نشده است.</p>}
        </div>
      </section>
    </div>
  );
}
