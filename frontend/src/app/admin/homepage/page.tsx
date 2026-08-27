"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/client-api";
import type { Brand, Category } from "@/lib/products";

type SectionType =
  | "banner"
  | "categories"
  | "brands"
  | "best_sellers"
  | "incredible_products"
  | "discounted_products"
  | "new_products"
  | "all_products"
  | "product_collection"
  | "brand_products"
  | "category_products"
  | "recently_viewed";

type Banner = {
  id: number;
  title: string | null;
  subtitle: string | null;
  // دو نسخه‌ی مستقل؛ فروشگاه بسته به عرض نمایشگر یکی را نشان می‌دهد
  desktopImage: string | null;
  mobileImage: string | null;
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

type BannerImageVariant = "desktop" | "mobile";

const BANNER_IMAGE_VARIANTS: {
  value: BannerImageVariant;
  label: string;
  hint: string;
}[] = [
  {
    value: "desktop",
    label: "تصویر بنر دسکتاپ",
    hint: "برای لپ‌تاپ و نمایشگرهای بزرگ — ترجیحاً عریض",
  },
  {
    value: "mobile",
    label: "تصویر بنر موبایل",
    hint: "برای موبایل و نمایشگرهای کوچک — نسخه‌ی جدا، نه برش دسکتاپ",
  },
];

const EMPTY_BANNER_IMAGES: Record<BannerImageVariant, File | null> = {
  desktop: null,
  mobile: null,
};

function bannerImageUrl(banner: Banner, variant: BannerImageVariant) {
  return variant === "desktop" ? banner.desktopImage : banner.mobileImage;
}

const SECTION_TYPES: { value: SectionType; label: string }[] = [
  { value: "banner", label: "بنر" },
  { value: "categories", label: "دسته‌بندی‌ها" },
  { value: "brands", label: "برندها" },
  { value: "best_sellers", label: "پرفروش‌ترین‌ها" },
  { value: "incredible_products", label: "شگفت‌انگیزها (منتخب مدیر)" },
  { value: "discounted_products", label: "همه محصولات تخفیف‌دار" },
  { value: "new_products", label: "جدیدترین محصولات" },
  { value: "all_products", label: "همه محصولات (صفحه‌بندی‌شده)" },
  { value: "product_collection", label: "مجموعه محصولات سفارشی" },
  { value: "brand_products", label: "محصولات یک برند" },
  { value: "category_products", label: "محصولات یک دسته‌بندی" },
  { value: "recently_viewed", label: "محصولات اخیراً مشاهده‌شده" },
];

/**
 * نوع بخش پس از ایجاد قابل تغییر نیست، جز این دو که فقط در مرجعشان فرق
 * دارند — مدیر می‌تواند بدون از دست دادن جای بخش، برند را با دسته‌بندی عوض کند.
 * هم‌تراز با INTERCHANGEABLE_SECTION_TYPES در بک‌اند.
 */
const INTERCHANGEABLE_TYPES: SectionType[] = ["brand_products", "category_products"];

function isInterchangeable(type: SectionType) {
  return INTERCHANGEABLE_TYPES.includes(type);
}

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

/**
 * پیش‌نمایش یک نسخه‌ی تصویر بنر — فایل تازه‌انتخاب‌شده اولویت دارد تا مدیر
 * پیش از ذخیره هم بتواند تصویر را ببیند؛ در غیر این صورت تصویر ذخیره‌شده.
 */
function BannerImagePreview({
  file,
  savedUrl,
}: {
  file: File | null;
  savedUrl: string | null;
}) {
  const objectUrl = useMemo(
    () => (file ? URL.createObjectURL(file) : null),
    [file]
  );

  useEffect(() => {
    if (!objectUrl) return;
    return () => URL.revokeObjectURL(objectUrl);
  }, [objectUrl]);

  const src = objectUrl ?? savedUrl;
  if (!src) {
    return (
      <span className="grid h-24 w-full place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-xs text-slate-400">
        بدون تصویر
      </span>
    );
  }
  return (
    <span className="block overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="" className="h-24 w-full object-contain" />
    </span>
  );
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
  const [bannerImages, setBannerImages] =
    useState<Record<BannerImageVariant, File | null>>(EMPTY_BANNER_IMAGES);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const fileInputs = useRef<Record<BannerImageVariant, HTMLInputElement | null>>({
    desktop: null,
    mobile: null,
  });
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

  function clearBannerImageInputs() {
    setBannerImages(EMPTY_BANNER_IMAGES);
    for (const input of Object.values(fileInputs.current)) {
      if (input) input.value = "";
    }
  }

  function resetBanner() {
    setEditingBanner(null);
    setBannerValues(EMPTY_BANNER);
    clearBannerImageInputs();
  }

  function editSection(section: Section) {
    setEditingSection(section);
    setSectionValues(sectionForm(section));
    sectionEditor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function editBanner(banner: Banner) {
    setEditingBanner(banner);
    setBannerValues(bannerForm(banner));
    clearBannerImageInputs();
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
    if (type === "brand_products") {
      if (!sectionValues.brandSlug) {
        notify("برای ردیف محصولات برند، یک برند انتخاب کنید");
        return;
      }
      payload.brandSlug = sectionValues.brandSlug;
    }
    if (type === "category_products") {
      if (!sectionValues.categorySlug) {
        notify("برای ردیف محصولات دسته‌بندی، یک دسته‌بندی انتخاب کنید");
        return;
      }
      payload.categorySlug = sectionValues.categorySlug;
    }
    // تعویض برند ↔ دسته‌بندی روی بخش موجود؛ بقیه‌ی انواع تغییرناپذیرند
    if (editingSection && type !== editingSection.sectionType) {
      payload.sectionType = type;
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
    const bannerId = result.data.banner.id;
    // هر نسخه‌ی تصویر جدا آپلود می‌شود؛ نسخه‌ی انتخاب‌نشده دست‌نخورده می‌ماند
    for (const variant of BANNER_IMAGE_VARIANTS) {
      const file = bannerImages[variant.value];
      if (!file) continue;
      const form = new FormData();
      form.append("file", file);
      const upload = await api.upload<{ banner: Banner }>(
        `/api/admin/home/banners/${bannerId}/image/${variant.value}`,
        form
      );
      if (!upload.ok) {
        setBusy(false);
        notify(
          `بنر ذخیره شد، اما ${variant.label} بارگذاری نشد: ${upload.error ?? "خطای نامشخص"}`
        );
        await load();
        return;
      }
    }
    setBusy(false);
    notify(editingBanner ? "بنر ویرایش شد ✅" : "بنر افزوده شد ✅");
    resetBanner();
    await load();
  }

  async function removeBannerImage(banner: Banner, variant: BannerImageVariant) {
    const label = BANNER_IMAGE_VARIANTS.find((item) => item.value === variant)?.label;
    if (busy || !window.confirm(`${label} حذف شود؟`)) return;
    setBusy(true);
    const result = await api.delete(
      `/api/admin/home/banners/${banner.id}/image/${variant}`
    );
    setBusy(false);
    if (!result.ok) {
      notify(result.error ?? "حذف تصویر انجام نشد");
      return;
    }
    notify("تصویر حذف شد ✅");
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
  // نسخه‌ی به‌روزِ بنر در حال ویرایش — بعد از هر load پیش‌نمایش‌ها تازه می‌شوند
  const editedBanner = editingBanner
    ? banners.find((item) => item.id === editingBanner.id) ?? editingBanner
    : null;

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
          <p className="p-6 text-center sm:p-8 text-sm text-slate-400">در حال دریافت...</p>
        ) : sections.length === 0 ? (
          <p className="p-6 text-center sm:p-8 text-sm text-slate-400">هنوز بخشی افزوده نشده است.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {sections.map((section, index) => (
              <div key={section.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">
                  {(index + 1).toLocaleString("fa-IR")}
                </span>
                <div className="min-w-0 flex-1 basis-44">
                  <p className="text-sm font-bold text-slate-700">
                    {section.resolvedTitle ?? SECTION_LABELS[section.sectionType]}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {SECTION_LABELS[section.sectionType]}
                    {section.sectionType === "brand_products" && section.brand ? ` · ${section.brand.name}` : ""}
                    {section.sectionType === "category_products" && section.category ? ` · ${section.category.title}` : ""}
                    {section.limit ? ` · حداکثر ${section.limit.toLocaleString("fa-IR")}` : ""}
                  </p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[11px] ${section.isActive ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {section.isActive ? "فعال" : "غیرفعال"}
                </span>
                <div className="flex w-full flex-wrap items-center justify-end gap-1 sm:w-auto">
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

      <section ref={sectionEditor} className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-bold text-slate-700">{editingSection ? "ویرایش بخش" : "افزودن بخش"}</h2>
          {editingSection && <button type="button" onClick={resetSection} className="text-xs text-slate-400">انصراف</button>}
        </div>
        <form onSubmit={saveSection} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">نوع بخش</span>
            <select disabled={editingSection !== null && !isInterchangeable(editingSection.sectionType)} value={type} onChange={(event) => setSectionValues((current) => ({ ...current, sectionType: event.target.value as SectionType }))} className={INPUT_CLASS}>
              {(editingSection && isInterchangeable(editingSection.sectionType)
                ? SECTION_TYPES.filter((item) => isInterchangeable(item.value))
                : SECTION_TYPES
              ).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">عنوان سفارشی (اختیاری)</span>
            <input value={sectionValues.title} onChange={(event) => setSectionValues((current) => ({ ...current, title: event.target.value }))} className={INPUT_CLASS} maxLength={150} placeholder="خالی = عنوان پیش‌فرض" />
          </label>
          {type === "banner" && (
            <label className="min-w-0 md:col-span-2">
              <span className="mb-1.5 block text-xs text-slate-600">بنر</span>
              <select required value={sectionValues.bannerId} onChange={(event) => setSectionValues((current) => ({ ...current, bannerId: event.target.value }))} className={INPUT_CLASS}>
                <option value="">انتخاب کنید</option>
                {banners.map((banner) => <option key={banner.id} value={banner.id}>{banner.title ?? `بنر #${banner.id}`}{banner.isActive ? "" : " (غیرفعال)"}</option>)}
              </select>
            </label>
          )}
          {type !== "banner" && (
            <label>
              <span className="mb-1.5 block text-xs text-slate-600">{type === "all_products" ? "تعداد در هر صفحه (۱ تا ۲۴)" : "حداکثر تعداد (۱ تا ۲۴)"}</span>
              <input type="number" min={1} max={24} value={sectionValues.limit} onChange={(event) => setSectionValues((current) => ({ ...current, limit: event.target.value }))} className={INPUT_CLASS} placeholder={isInterchangeable(type) ? "۶ (پیش‌فرض)" : "پیش‌فرض"} />
            </label>
          )}
          {type === "brand_products" && (
            <label className="min-w-0">
              <span className="mb-1.5 block text-xs text-slate-600">برند</span>
              <select required value={sectionValues.brandSlug} onChange={(event) => setSectionValues((current) => ({ ...current, brandSlug: event.target.value }))} className={INPUT_CLASS}>
                <option value="">انتخاب کنید</option>
                {brands.map((brand) => <option key={brand.slug} value={brand.slug}>{brand.name}</option>)}
              </select>
            </label>
          )}
          {type === "category_products" && (
            <label className="min-w-0">
              <span className="mb-1.5 block text-xs text-slate-600">دسته‌بندی</span>
              <select required value={sectionValues.categorySlug} onChange={(event) => setSectionValues((current) => ({ ...current, categorySlug: event.target.value }))} className={INPUT_CLASS}>
                <option value="">انتخاب کنید</option>
                {categories.map((category) => <option key={category.slug} value={category.slug}>{category.title}</option>)}
              </select>
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
          <div className="min-w-0 md:col-span-2">
            <button disabled={busy} className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">{busy ? "در حال ذخیره..." : editingSection ? "ذخیره تغییرات" : "افزودن به انتهای صفحه"}</button>
          </div>
        </form>
      </section>

      <section ref={bannerEditor} className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-5">
        <div className="mb-4 flex items-center justify-between">
          <div><h2 className="font-bold text-slate-700">{editingBanner ? "ویرایش بنر" : "ساخت بنر"}</h2><p className="mt-1 text-[11px] text-slate-400">یک بنر را می‌توان در چند جای صفحه اصلی استفاده کرد.</p></div>
          {editingBanner && <button type="button" onClick={resetBanner} className="text-xs text-slate-400">انصراف</button>}
        </div>
        <form onSubmit={saveBanner} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label><span className="mb-1.5 block text-xs text-slate-600">عنوان</span><input value={bannerValues.title} onChange={(event) => setBannerValues((current) => ({ ...current, title: event.target.value }))} className={INPUT_CLASS} maxLength={150} /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">زیرعنوان</span><input value={bannerValues.subtitle} onChange={(event) => setBannerValues((current) => ({ ...current, subtitle: event.target.value }))} className={INPUT_CLASS} maxLength={300} /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">لینک مقصد</span><input dir="ltr" value={bannerValues.linkUrl} onChange={(event) => setBannerValues((current) => ({ ...current, linkUrl: event.target.value }))} className={INPUT_CLASS} placeholder="/category/..." /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">متن دکمه</span><input value={bannerValues.linkLabel} onChange={(event) => setBannerValues((current) => ({ ...current, linkLabel: event.target.value }))} className={INPUT_CLASS} maxLength={60} /></label>
          <label><span className="mb-1.5 block text-xs text-slate-600">رنگ زمینه</span><select value={bannerValues.theme} onChange={(event) => setBannerValues((current) => ({ ...current, theme: event.target.value as Banner["theme"] }))} className={INPUT_CLASS}><option value="brand">سبز برند</option><option value="secondary">آبی</option><option value="accent">طلایی</option></select></label>
          {BANNER_IMAGE_VARIANTS.map((variant) => {
            const savedUrl = editedBanner ? bannerImageUrl(editedBanner, variant.value) : null;
            return (
              <div key={variant.value} className="min-w-0 space-y-1.5">
                <label className="block">
                  <span className="block text-xs text-slate-600">{variant.label} (اختیاری، حداکثر ۵ مگابایت)</span>
                  <span className="mt-0.5 mb-1.5 block text-[11px] text-slate-400">{variant.hint}</span>
                  <input ref={(node) => { fileInputs.current[variant.value] = node; }} type="file" accept="image/*" onChange={(event) => { const file = event.target.files?.[0] ?? null; setBannerImages((current) => ({ ...current, [variant.value]: file })); }} className={INPUT_CLASS} />
                </label>
                <BannerImagePreview file={bannerImages[variant.value]} savedUrl={savedUrl} />
                {savedUrl && editedBanner && (
                  <button type="button" disabled={busy} onClick={() => removeBannerImage(editedBanner, variant.value)} className="text-[11px] text-red-600 disabled:opacity-50">حذف {variant.label}</button>
                )}
              </div>
            );
          })}
          <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={bannerValues.isActive} onChange={(event) => setBannerValues((current) => ({ ...current, isActive: event.target.checked }))} />بنر فعال باشد</label>
          <div className="min-w-0 md:col-span-2"><button disabled={busy} className="rounded-xl bg-secondary-900 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50">{busy ? "در حال ذخیره..." : editingBanner ? "ذخیره بنر" : "ساخت بنر"}</button></div>
        </form>
      </section>

      <section className="rounded-2xl border border-slate-100 bg-white p-5">
        <h2 className="mb-4 font-bold text-slate-700">بنرهای موجود</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {banners.map((banner) => (
            <article key={banner.id} className="flex min-w-0 gap-3 rounded-xl border border-slate-100 p-3">
              <div className="flex shrink-0 gap-2">
                {BANNER_IMAGE_VARIANTS.map((variant) => {
                  const url = bannerImageUrl(banner, variant.value);
                  return (
                    <div key={variant.value} className="w-24 shrink-0">
                      {url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={url} alt="" className="h-16 w-24 rounded-lg object-cover" />
                      ) : (
                        <span className="grid h-16 w-24 place-items-center rounded-lg bg-brand-50 text-2xl">🚜</span>
                      )}
                      <p className="mt-1 text-center text-[10px] text-slate-400">{variant.value === "desktop" ? "دسکتاپ" : "موبایل"}</p>
                    </div>
                  );
                })}
              </div>
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold text-slate-700">{banner.title ?? `بنر #${banner.id}`}</p><p className="mt-1 text-[11px] text-slate-400">استفاده در {banner.sectionCount.toLocaleString("fa-IR")} بخش · {banner.isActive ? "فعال" : "غیرفعال"}</p><div className="mt-2 flex gap-2"><button type="button" onClick={() => editBanner(banner)} className="text-xs text-brand-700">ویرایش</button><button type="button" disabled={busy} onClick={() => removeBanner(banner)} className="text-xs text-red-600">حذف</button></div></div>
            </article>
          ))}
          {!banners.length && <p className="text-sm text-slate-400">هنوز بنری ساخته نشده است.</p>}
        </div>
      </section>
    </div>
  );
}
