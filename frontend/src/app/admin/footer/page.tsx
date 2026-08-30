"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/client-api";

type SectionVariant = "column" | "strip";

type ItemType =
  | "link"
  | "text"
  | "image"
  | "phone"
  | "email"
  | "address"
  | "social";

type FooterItem = {
  id: number;
  sectionId: number;
  type: ItemType;
  label: string | null;
  text: string | null;
  url: string | null;
  rawUrl: string | null;
  image: string | null;
  icon: string | null;
  openInNewTab: boolean;
  isExternal: boolean;
  staticPageKey: string | null;
  isActive: boolean;
  position: number;
};

type FooterSection = {
  id: number;
  title: string | null;
  variant: SectionVariant;
  description: string | null;
  position: number;
  isActive: boolean;
  items: FooterItem[];
};

type FooterSettings = {
  brandTitle: string | null;
  logo: string | null;
  description: string | null;
  copyright: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  storedBrandTitle: string | null;
  storedCopyright: string | null;
};

type PageSummary = { key: string; label: string };

type SectionForm = {
  title: string;
  variant: SectionVariant;
  description: string;
  isActive: boolean;
};

type ItemForm = {
  itemType: ItemType;
  label: string;
  url: string;
  text: string;
  icon: string;
  openInNewTab: boolean;
  staticPageKey: string;
  isActive: boolean;
};

type SettingsForm = {
  brandTitle: string;
  description: string;
  copyrightText: string;
  address: string;
  phone: string;
  email: string;
};

const VARIANTS: { value: SectionVariant; label: string; hint: string }[] = [
  {
    value: "column",
    label: "ستون",
    hint: "یک ستون با عنوان و فهرست عمودی — مثل «خدمات مشتریان»",
  },
  {
    value: "strip",
    label: "نوار مزیت‌ها",
    hint: "ردیف افقی آیکن‌دار در بالای فوتر — مثل «ارسال به سراسر کشور»",
  },
];

/**
 * فیلدهای هر نوع محتوا — هم‌تراز با _TYPE_ALLOWED_FIELDS در بک‌اند. افزودن
 * نوع تازه یعنی یک ردیف اینجا، نه یک شاخه‌ی if در فرم.
 */
const ITEM_TYPES: {
  value: ItemType;
  label: string;
  fields: (keyof ItemForm | "image")[];
  textLabel?: string;
  textDir?: "ltr";
}[] = [
  {
    value: "link",
    label: "پیوند",
    fields: ["label", "url", "icon", "openInNewTab", "staticPageKey"],
  },
  {
    value: "social",
    label: "شبکه اجتماعی",
    fields: ["label", "url", "icon", "openInNewTab"],
  },
  { value: "text", label: "متن", fields: ["label", "text", "icon"] },
  {
    value: "address",
    label: "نشانی",
    fields: ["label", "text", "icon"],
    textLabel: "نشانی",
  },
  {
    value: "phone",
    label: "شماره تماس",
    fields: ["label", "text", "icon"],
    textLabel: "شماره تماس",
    textDir: "ltr",
  },
  {
    value: "email",
    label: "ایمیل",
    fields: ["label", "text", "icon"],
    textLabel: "ایمیل",
    textDir: "ltr",
  },
  {
    value: "image",
    label: "تصویر / لوگو",
    fields: ["label", "url", "image", "openInNewTab"],
  },
];

const ITEM_TYPE_LABELS = Object.fromEntries(
  ITEM_TYPES.map((item) => [item.value, item.label])
) as Record<ItemType, string>;

function itemDefinition(type: ItemType) {
  return ITEM_TYPES.find((item) => item.value === type) ?? ITEM_TYPES[0];
}

const EMPTY_SECTION: SectionForm = {
  title: "",
  variant: "column",
  description: "",
  isActive: true,
};

const EMPTY_ITEM: ItemForm = {
  itemType: "link",
  label: "",
  url: "",
  text: "",
  icon: "",
  openInNewTab: false,
  staticPageKey: "",
  isActive: true,
};

const EMPTY_SETTINGS: SettingsForm = {
  brandTitle: "",
  description: "",
  copyrightText: "",
  address: "",
  phone: "",
  email: "",
};

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white disabled:opacity-60";
const SMALL_BUTTON = "rounded-lg border px-2.5 py-1.5 text-xs disabled:opacity-30";

function sectionForm(section: FooterSection): SectionForm {
  return {
    title: section.title ?? "",
    variant: section.variant,
    description: section.description ?? "",
    isActive: section.isActive,
  };
}

function itemForm(item: FooterItem): ItemForm {
  return {
    itemType: item.type,
    label: item.label ?? "",
    url: item.rawUrl ?? "",
    text: item.text ?? "",
    icon: item.icon ?? "",
    openInNewTab: item.openInNewTab,
    staticPageKey: item.staticPageKey ?? "",
    isActive: item.isActive,
  };
}

function settingsForm(settings: FooterSettings): SettingsForm {
  return {
    brandTitle: settings.storedBrandTitle ?? "",
    description: settings.description ?? "",
    copyrightText: settings.storedCopyright ?? "",
    address: settings.address ?? "",
    phone: settings.phone ?? "",
    email: settings.email ?? "",
  };
}

/** پیش‌نمایش تصویر — فایل تازه‌انتخاب‌شده بر تصویر ذخیره‌شده اولویت دارد */
function ImagePreview({
  file,
  savedUrl,
  className = "h-16 w-full",
}: {
  file: File | null;
  savedUrl: string | null;
  className?: string;
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
      <span
        className={`grid ${className} place-items-center rounded-xl border border-dashed border-slate-200 bg-slate-50 text-xs text-slate-400`}
      >
        بدون تصویر
      </span>
    );
  }
  return (
    <span className="block overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="" className={`${className} object-contain`} />
    </span>
  );
}

function itemSummary(item: FooterItem): string {
  const parts = [ITEM_TYPE_LABELS[item.type] ?? item.type];
  if (item.rawUrl) parts.push(item.rawUrl);
  else if (item.text) parts.push(item.text.slice(0, 40));
  if (item.openInNewTab) parts.push("تب جدید");
  return parts.join(" · ");
}

export default function AdminFooterPage() {
  const [sections, setSections] = useState<FooterSection[]>([]);
  const [settings, setSettings] = useState<FooterSettings | null>(null);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [settingsValues, setSettingsValues] = useState(EMPTY_SETTINGS);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [sectionValues, setSectionValues] = useState(EMPTY_SECTION);
  const [editingSection, setEditingSection] = useState<FooterSection | null>(null);
  const [itemValues, setItemValues] = useState(EMPTY_ITEM);
  const [editingItem, setEditingItem] = useState<FooterItem | null>(null);
  const [itemSectionId, setItemSectionId] = useState<number | null>(null);
  const [itemImage, setItemImage] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const logoInput = useRef<HTMLInputElement>(null);
  const itemImageInput = useRef<HTMLInputElement>(null);
  const sectionEditor = useRef<HTMLElement>(null);
  const itemEditor = useRef<HTMLElement>(null);

  const notify = useCallback((text: string) => {
    setMessage(text);
    window.setTimeout(() => setMessage(""), 5000);
  }, []);

  const load = useCallback(async () => {
    const [sectionResult, settingsResult, pageResult] = await Promise.all([
      api.get<{ sections: FooterSection[] }>("/api/admin/footer/sections"),
      api.get<{ settings: FooterSettings }>("/api/admin/footer/settings"),
      api.get<{ pages: PageSummary[] }>("/api/admin/content/pages"),
    ]);
    if (sectionResult.ok) setSections(sectionResult.data?.sections ?? []);
    if (settingsResult.ok && settingsResult.data) {
      setSettings(settingsResult.data.settings);
      setSettingsValues(settingsForm(settingsResult.data.settings));
    }
    if (pageResult.ok) setPages(pageResult.data?.pages ?? []);
    const failure = [sectionResult, settingsResult, pageResult].find(
      (result) => !result.ok
    );
    if (failure) notify(failure.error ?? "دریافت اطلاعات فوتر انجام نشد");
    setLoading(false);
  }, [notify]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  // ─────────────────────────────── تنظیمات سراسری

  async function saveSettings(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    const result = await api.patch<{ settings: FooterSettings }>(
      "/api/admin/footer/settings",
      {
        brandTitle: settingsValues.brandTitle.trim(),
        description: settingsValues.description.trim(),
        copyrightText: settingsValues.copyrightText.trim(),
        address: settingsValues.address.trim(),
        phone: settingsValues.phone.trim(),
        email: settingsValues.email.trim(),
      }
    );
    if (!result.ok) {
      setBusy(false);
      notify(result.error ?? "ذخیره تنظیمات انجام نشد");
      return;
    }
    if (logoFile) {
      const form = new FormData();
      form.append("file", logoFile);
      const upload = await api.upload("/api/admin/footer/settings/logo", form);
      if (!upload.ok) {
        setBusy(false);
        notify(`تنظیمات ذخیره شد، اما لوگو بارگذاری نشد: ${upload.error ?? ""}`);
        await load();
        return;
      }
    }
    setBusy(false);
    setLogoFile(null);
    if (logoInput.current) logoInput.current.value = "";
    notify("تنظیمات فوتر ذخیره شد ✅");
    await load();
  }

  async function removeLogo() {
    if (busy || !window.confirm("لوگوی فوتر حذف شود؟")) return;
    setBusy(true);
    const result = await api.delete("/api/admin/footer/settings/logo");
    setBusy(false);
    if (!result.ok) notify(result.error ?? "حذف لوگو انجام نشد");
    else {
      notify("لوگو حذف شد ✅");
      await load();
    }
  }

  // ────────────────────────────────────── بخش‌ها

  function resetSection() {
    setEditingSection(null);
    setSectionValues(EMPTY_SECTION);
  }

  function editSection(section: FooterSection) {
    setEditingSection(section);
    setSectionValues(sectionForm(section));
    sectionEditor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveSection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    const payload = {
      title: sectionValues.title.trim(),
      variant: sectionValues.variant,
      description: sectionValues.description.trim(),
      isActive: sectionValues.isActive,
    };
    const result = editingSection
      ? await api.patch(`/api/admin/footer/sections/${editingSection.id}`, payload)
      : await api.post("/api/admin/footer/sections", payload);
    setBusy(false);
    if (!result.ok) {
      notify(result.error ?? "ذخیره بخش انجام نشد");
      return;
    }
    notify(editingSection ? "بخش ویرایش شد ✅" : "بخش افزوده شد ✅");
    resetSection();
    await load();
  }

  async function toggleSection(section: FooterSection) {
    if (busy) return;
    setBusy(true);
    const result = await api.patch(`/api/admin/footer/sections/${section.id}`, {
      isActive: !section.isActive,
    });
    setBusy(false);
    if (!result.ok) notify(result.error ?? "تغییر وضعیت انجام نشد");
    else await load();
  }

  async function moveSection(section: FooterSection, direction: "up" | "down") {
    if (busy) return;
    setBusy(true);
    const result = await api.post<{ sections: FooterSection[] }>(
      `/api/admin/footer/sections/${section.id}/move`,
      { direction }
    );
    setBusy(false);
    if (!result.ok) notify(result.error ?? "تغییر ترتیب انجام نشد");
    else setSections(result.data?.sections ?? []);
  }

  async function removeSection(section: FooterSection) {
    const usage = section.items.length
      ? ` ${section.items.length.toLocaleString("fa-IR")} محتوای داخل آن هم حذف می‌شود.`
      : "";
    if (!window.confirm(`بخش «${section.title ?? "بدون عنوان"}» حذف شود؟${usage}`))
      return;
    setBusy(true);
    const result = await api.delete(`/api/admin/footer/sections/${section.id}`);
    setBusy(false);
    if (!result.ok) notify(result.error ?? "حذف بخش انجام نشد");
    else {
      if (editingSection?.id === section.id) resetSection();
      if (itemSectionId === section.id) resetItem();
      await load();
    }
  }

  // ─────────────────────────────────────── محتوا

  function resetItem() {
    setEditingItem(null);
    setItemSectionId(null);
    setItemValues(EMPTY_ITEM);
    setItemImage(null);
    if (itemImageInput.current) itemImageInput.current.value = "";
  }

  function addItem(section: FooterSection) {
    setEditingItem(null);
    setItemSectionId(section.id);
    setItemValues(EMPTY_ITEM);
    setItemImage(null);
    itemEditor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function editItem(item: FooterItem) {
    setEditingItem(item);
    setItemSectionId(item.sectionId);
    setItemValues(itemForm(item));
    setItemImage(null);
    if (itemImageInput.current) itemImageInput.current.value = "";
    itemEditor.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function saveItem(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || itemSectionId === null) return;
    const definition = itemDefinition(itemValues.itemType);
    const allowed = new Set(definition.fields);
    const payload: Record<string, unknown> = {
      itemType: itemValues.itemType,
      isActive: itemValues.isActive,
      label: allowed.has("label") ? itemValues.label.trim() : "",
      url: allowed.has("url") ? itemValues.url.trim() : "",
      text: allowed.has("text") ? itemValues.text.trim() : "",
      icon: allowed.has("icon") ? itemValues.icon.trim() : "",
      openInNewTab: allowed.has("openInNewTab") ? itemValues.openInNewTab : false,
      staticPageKey: allowed.has("staticPageKey") ? itemValues.staticPageKey : "",
    };
    if (itemValues.itemType === "image" && !editingItem && !itemImage) {
      notify("برای محتوای تصویری، یک تصویر انتخاب کنید");
      return;
    }

    setBusy(true);
    const result = editingItem
      ? await api.patch<{ item: FooterItem }>(
          `/api/admin/footer/items/${editingItem.id}`,
          payload
        )
      : await api.post<{ item: FooterItem }>(
          `/api/admin/footer/sections/${itemSectionId}/items`,
          payload
        );
    if (!result.ok || !result.data) {
      setBusy(false);
      notify(result.error ?? "ذخیره محتوا انجام نشد");
      return;
    }
    if (itemImage) {
      const form = new FormData();
      form.append("file", itemImage);
      const upload = await api.upload(
        `/api/admin/footer/items/${result.data.item.id}/image`,
        form
      );
      if (!upload.ok) {
        setBusy(false);
        notify(`محتوا ذخیره شد، اما تصویر بارگذاری نشد: ${upload.error ?? ""}`);
        await load();
        return;
      }
    }
    setBusy(false);
    notify(editingItem ? "محتوا ویرایش شد ✅" : "محتوا افزوده شد ✅");
    resetItem();
    await load();
  }

  async function toggleItem(item: FooterItem) {
    if (busy) return;
    setBusy(true);
    const result = await api.patch(`/api/admin/footer/items/${item.id}`, {
      isActive: !item.isActive,
    });
    setBusy(false);
    if (!result.ok) notify(result.error ?? "تغییر وضعیت انجام نشد");
    else await load();
  }

  async function moveItem(item: FooterItem, direction: "up" | "down") {
    if (busy) return;
    setBusy(true);
    const result = await api.post(`/api/admin/footer/items/${item.id}/move`, {
      direction,
    });
    setBusy(false);
    if (!result.ok) notify(result.error ?? "تغییر ترتیب انجام نشد");
    else await load();
  }

  async function removeItem(item: FooterItem) {
    if (!window.confirm(`«${item.label ?? item.text ?? "این محتوا"}» حذف شود؟`))
      return;
    setBusy(true);
    const result = await api.delete(`/api/admin/footer/items/${item.id}`);
    setBusy(false);
    if (!result.ok) notify(result.error ?? "حذف محتوا انجام نشد");
    else {
      if (editingItem?.id === item.id) resetItem();
      await load();
    }
  }

  const itemDefinitionFields = new Set(itemDefinition(itemValues.itemType).fields);
  const activeItemDefinition = itemDefinition(itemValues.itemType);
  const editingSectionTitle =
    sections.find((section) => section.id === itemSectionId)?.title ?? "بدون عنوان";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-bold text-slate-800">مدیریت فوتر</h1>
        <p className="mt-1 text-xs leading-6 text-slate-400">
          ساختار و محتوای فوتر فروشگاه از همین‌جا ساخته می‌شود؛ بخش غیرفعال یا
          حذف‌شده بلافاصله از سایت حذف می‌شود.
        </p>
      </div>

      {message && (
        <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">
          {message}
        </p>
      )}

      {/* ─── تنظیمات سراسری ─── */}
      <section className="rounded-2xl border border-slate-100 bg-white p-5">
        <h2 className="mb-1 font-bold text-slate-700">تنظیمات سراسری</h2>
        <p className="mb-4 text-[11px] text-slate-400">
          لوگو، معرفی کوتاه، اطلاعات تماس و کپی‌رایتِ پایین فوتر.
        </p>
        <form onSubmit={saveSettings} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">نام برند</span>
            <input
              value={settingsValues.brandTitle}
              onChange={(event) =>
                setSettingsValues((current) => ({
                  ...current,
                  brandTitle: event.target.value,
                }))
              }
              maxLength={120}
              placeholder="خالی = نام سایت از تنظیمات سئو"
              className={INPUT_CLASS}
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">
              متن کپی‌رایت ({"{year}"} و {"{brand}"} جایگزین می‌شوند)
            </span>
            <input
              value={settingsValues.copyrightText}
              onChange={(event) =>
                setSettingsValues((current) => ({
                  ...current,
                  copyrightText: event.target.value,
                }))
              }
              maxLength={200}
              placeholder={settings?.copyright ?? ""}
              className={INPUT_CLASS}
            />
          </label>
          <label className="md:col-span-2">
            <span className="mb-1.5 block text-xs text-slate-600">معرفی کوتاه</span>
            <textarea
              value={settingsValues.description}
              onChange={(event) =>
                setSettingsValues((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              maxLength={600}
              rows={3}
              className={INPUT_CLASS}
            />
          </label>
          <label className="md:col-span-2">
            <span className="mb-1.5 block text-xs text-slate-600">نشانی</span>
            <input
              value={settingsValues.address}
              onChange={(event) =>
                setSettingsValues((current) => ({
                  ...current,
                  address: event.target.value,
                }))
              }
              maxLength={300}
              className={INPUT_CLASS}
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">تلفن</span>
            <input
              dir="ltr"
              value={settingsValues.phone}
              onChange={(event) =>
                setSettingsValues((current) => ({
                  ...current,
                  phone: event.target.value,
                }))
              }
              maxLength={40}
              className={INPUT_CLASS}
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">ایمیل</span>
            <input
              dir="ltr"
              value={settingsValues.email}
              onChange={(event) =>
                setSettingsValues((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
              maxLength={120}
              className={INPUT_CLASS}
            />
          </label>
          <div className="min-w-0 space-y-1.5">
            <label className="block">
              <span className="block text-xs text-slate-600">
                لوگو (اختیاری، حداکثر ۲ مگابایت)
              </span>
              <span className="mt-0.5 mb-1.5 block text-[11px] text-slate-400">
                خالی = لوگوی پیش‌فرض فروشگاه
              </span>
              <input
                ref={logoInput}
                type="file"
                accept="image/*"
                onChange={(event) => setLogoFile(event.target.files?.[0] ?? null)}
                className={INPUT_CLASS}
              />
            </label>
            <ImagePreview
              file={logoFile}
              savedUrl={settings?.logo ?? null}
              className="h-20 w-full"
            />
            {settings?.logo && (
              <button
                type="button"
                disabled={busy}
                onClick={removeLogo}
                className="text-[11px] text-red-600 disabled:opacity-50"
              >
                حذف لوگو
              </button>
            )}
          </div>
          <div className="min-w-0 self-end md:col-span-2">
            <button
              disabled={busy}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {busy ? "در حال ذخیره..." : "ذخیره تنظیمات"}
            </button>
          </div>
        </form>
      </section>

      {/* ─── فهرست بخش‌ها ─── */}
      <section className="overflow-hidden rounded-2xl border border-slate-100 bg-white">
        <div className="border-b border-slate-100 px-5 py-4 font-bold text-slate-700">
          بخش‌های فوتر
        </div>
        {loading ? (
          <p className="p-6 text-center text-sm text-slate-400 sm:p-8">
            در حال دریافت...
          </p>
        ) : sections.length === 0 ? (
          <p className="p-6 text-center text-sm text-slate-400 sm:p-8">
            هنوز بخشی افزوده نشده است.
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {sections.map((section, index) => (
              <div key={section.id} className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-100 text-xs font-bold text-slate-500">
                    {(index + 1).toLocaleString("fa-IR")}
                  </span>
                  <div className="min-w-0 flex-1 basis-44">
                    <p className="text-sm font-bold text-slate-700">
                      {section.title ?? "بدون عنوان"}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {VARIANTS.find((item) => item.value === section.variant)?.label ??
                        section.variant}
                      {` · ${section.items.length.toLocaleString("fa-IR")} محتوا`}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-[11px] ${
                      section.isActive
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {section.isActive ? "فعال" : "غیرفعال"}
                  </span>
                  <div className="flex w-full flex-wrap items-center justify-end gap-1 sm:w-auto">
                    <button
                      type="button"
                      disabled={busy || index === 0}
                      onClick={() => moveSection(section, "up")}
                      title="انتقال به بالا"
                      className={`${SMALL_BUTTON} border-slate-200`}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      disabled={busy || index === sections.length - 1}
                      onClick={() => moveSection(section, "down")}
                      title="انتقال به پایین"
                      className={`${SMALL_BUTTON} border-slate-200`}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => toggleSection(section)}
                      className={`${SMALL_BUTTON} border-slate-200 text-slate-600`}
                    >
                      {section.isActive ? "غیرفعال" : "فعال"}
                    </button>
                    <button
                      type="button"
                      onClick={() => editSection(section)}
                      className={`${SMALL_BUTTON} border-brand-200 text-brand-700`}
                    >
                      ویرایش
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => removeSection(section)}
                      className={`${SMALL_BUTTON} border-red-100 text-red-600`}
                    >
                      حذف
                    </button>
                  </div>
                </div>

                <ul className="mt-3 space-y-1.5 border-r border-slate-100 pr-4 sm:mr-8">
                  {section.items.map((item, itemIndex) => (
                    <li
                      key={item.id}
                      className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50/70 px-3 py-2"
                    >
                      <div className="min-w-0 flex-1 basis-40">
                        <p className="truncate text-xs font-medium text-slate-700">
                          {item.icon && <span className="ml-1">{item.icon}</span>}
                          {item.label ?? item.text ?? "—"}
                        </p>
                        <p
                          dir="auto"
                          className="mt-0.5 truncate text-[11px] text-slate-400"
                        >
                          {itemSummary(item)}
                        </p>
                      </div>
                      {!item.isActive && (
                        <span className="rounded-full bg-slate-200 px-2 py-0.5 text-[10px] text-slate-500">
                          غیرفعال
                        </span>
                      )}
                      <div className="flex flex-wrap items-center gap-1">
                        <button
                          type="button"
                          disabled={busy || itemIndex === 0}
                          onClick={() => moveItem(item, "up")}
                          title="انتقال به بالا"
                          className={`${SMALL_BUTTON} border-slate-200 bg-white`}
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          disabled={busy || itemIndex === section.items.length - 1}
                          onClick={() => moveItem(item, "down")}
                          title="انتقال به پایین"
                          className={`${SMALL_BUTTON} border-slate-200 bg-white`}
                        >
                          ↓
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => toggleItem(item)}
                          className={`${SMALL_BUTTON} border-slate-200 bg-white text-slate-600`}
                        >
                          {item.isActive ? "غیرفعال" : "فعال"}
                        </button>
                        <button
                          type="button"
                          onClick={() => editItem(item)}
                          className={`${SMALL_BUTTON} border-brand-200 bg-white text-brand-700`}
                        >
                          ویرایش
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => removeItem(item)}
                          className={`${SMALL_BUTTON} border-red-100 bg-white text-red-600`}
                        >
                          حذف
                        </button>
                      </div>
                    </li>
                  ))}
                  <li>
                    <button
                      type="button"
                      onClick={() => addItem(section)}
                      className="rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-[11px] text-slate-500 transition hover:border-brand-400 hover:text-brand-700"
                    >
                      + افزودن محتوا به این بخش
                    </button>
                  </li>
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ─── ویرایشگر بخش ─── */}
      <section
        ref={sectionEditor}
        className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-5"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-bold text-slate-700">
            {editingSection ? "ویرایش بخش" : "افزودن بخش"}
          </h2>
          {editingSection && (
            <button type="button" onClick={resetSection} className="text-xs text-slate-400">
              انصراف
            </button>
          )}
        </div>
        <form onSubmit={saveSection} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">عنوان بخش</span>
            <input
              value={sectionValues.title}
              onChange={(event) =>
                setSectionValues((current) => ({
                  ...current,
                  title: event.target.value,
                }))
              }
              maxLength={120}
              className={INPUT_CLASS}
              placeholder={
                sectionValues.variant === "strip" ? "اختیاری" : "مثلاً خدمات مشتریان"
              }
            />
          </label>
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">چیدمان</span>
            <select
              value={sectionValues.variant}
              onChange={(event) =>
                setSectionValues((current) => ({
                  ...current,
                  variant: event.target.value as SectionVariant,
                }))
              }
              className={INPUT_CLASS}
            >
              {VARIANTS.map((variant) => (
                <option key={variant.value} value={variant.value}>
                  {variant.label}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-[11px] text-slate-400">
              {VARIANTS.find((item) => item.value === sectionValues.variant)?.hint}
            </span>
          </label>
          <label className="md:col-span-2">
            <span className="mb-1.5 block text-xs text-slate-600">
              توضیح زیر عنوان (اختیاری)
            </span>
            <textarea
              value={sectionValues.description}
              onChange={(event) =>
                setSectionValues((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              maxLength={400}
              rows={2}
              className={INPUT_CLASS}
            />
          </label>
          <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={sectionValues.isActive}
              onChange={(event) =>
                setSectionValues((current) => ({
                  ...current,
                  isActive: event.target.checked,
                }))
              }
            />
            بخش فعال باشد
          </label>
          <div className="min-w-0 md:col-span-2">
            <button
              disabled={busy}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {busy
                ? "در حال ذخیره..."
                : editingSection
                  ? "ذخیره تغییرات"
                  : "افزودن به انتهای فوتر"}
            </button>
          </div>
        </form>
      </section>

      {/* ─── ویرایشگر محتوا ─── */}
      <section
        ref={itemEditor}
        className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-5"
      >
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-slate-700">
              {editingItem ? "ویرایش محتوا" : "افزودن محتوا"}
            </h2>
            <p className="mt-1 text-[11px] text-slate-400">
              {itemSectionId === null
                ? "ابتدا از فهرست بالا، «افزودن محتوا» یک بخش را بزنید."
                : `بخش: ${editingSectionTitle}`}
            </p>
          </div>
          {itemSectionId !== null && (
            <button type="button" onClick={resetItem} className="text-xs text-slate-400">
              انصراف
            </button>
          )}
        </div>
        <form
          onSubmit={saveItem}
          className="grid grid-cols-1 gap-4 md:grid-cols-2"
        >
          <label>
            <span className="mb-1.5 block text-xs text-slate-600">نوع محتوا</span>
            <select
              disabled={itemSectionId === null}
              value={itemValues.itemType}
              onChange={(event) =>
                setItemValues((current) => ({
                  ...current,
                  itemType: event.target.value as ItemType,
                }))
              }
              className={INPUT_CLASS}
            >
              {ITEM_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          {itemDefinitionFields.has("label") && (
            <label>
              <span className="mb-1.5 block text-xs text-slate-600">
                {itemValues.itemType === "image" ? "متن جایگزین تصویر" : "عنوان"}
              </span>
              <input
                disabled={itemSectionId === null}
                value={itemValues.label}
                onChange={(event) =>
                  setItemValues((current) => ({ ...current, label: event.target.value }))
                }
                maxLength={120}
                className={INPUT_CLASS}
              />
            </label>
          )}
          {itemDefinitionFields.has("url") && (
            <label className="md:col-span-2">
              <span className="mb-1.5 block text-xs text-slate-600">
                نشانی مقصد (مسیر داخلی مثل /support یا آدرس کامل https://...)
              </span>
              <input
                dir="ltr"
                disabled={itemSectionId === null}
                value={itemValues.url}
                onChange={(event) =>
                  setItemValues((current) => ({ ...current, url: event.target.value }))
                }
                maxLength={300}
                className={INPUT_CLASS}
              />
            </label>
          )}
          {itemDefinitionFields.has("text") && (
            <label className="md:col-span-2">
              <span className="mb-1.5 block text-xs text-slate-600">
                {activeItemDefinition.textLabel ?? "متن"}
              </span>
              <textarea
                dir={activeItemDefinition.textDir}
                disabled={itemSectionId === null}
                value={itemValues.text}
                onChange={(event) =>
                  setItemValues((current) => ({ ...current, text: event.target.value }))
                }
                maxLength={600}
                rows={activeItemDefinition.textDir ? 1 : 3}
                className={INPUT_CLASS}
              />
            </label>
          )}
          {itemDefinitionFields.has("icon") && (
            <label>
              <span className="mb-1.5 block text-xs text-slate-600">
                آیکن (یک ایموجی، اختیاری)
              </span>
              <input
                disabled={itemSectionId === null}
                value={itemValues.icon}
                onChange={(event) =>
                  setItemValues((current) => ({ ...current, icon: event.target.value }))
                }
                maxLength={32}
                className={INPUT_CLASS}
                placeholder="🚚"
              />
            </label>
          )}
          {itemDefinitionFields.has("staticPageKey") && (
            <label>
              <span className="mb-1.5 block text-xs text-slate-600">
                وابسته به صفحه محتوایی (اختیاری)
              </span>
              <select
                disabled={itemSectionId === null}
                value={itemValues.staticPageKey}
                onChange={(event) =>
                  setItemValues((current) => ({
                    ...current,
                    staticPageKey: event.target.value,
                  }))
                }
                className={INPUT_CLASS}
              >
                <option value="">وابسته نیست</option>
                {pages.map((page) => (
                  <option key={page.key} value={page.key}>
                    {page.label}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-[11px] text-slate-400">
                اگر آن صفحه در «محتوای صفحات» پنهان شود، این پیوند هم پنهان می‌شود.
              </span>
            </label>
          )}
          {itemDefinitionFields.has("image") && (
            <div className="min-w-0 space-y-1.5">
              <label className="block">
                <span className="block text-xs text-slate-600">
                  تصویر (حداکثر ۲ مگابایت)
                </span>
                <input
                  ref={itemImageInput}
                  type="file"
                  accept="image/*"
                  disabled={itemSectionId === null}
                  onChange={(event) => setItemImage(event.target.files?.[0] ?? null)}
                  className={INPUT_CLASS}
                />
              </label>
              <ImagePreview file={itemImage} savedUrl={editingItem?.image ?? null} />
            </div>
          )}
          {itemDefinitionFields.has("openInNewTab") && (
            <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-600">
              <input
                type="checkbox"
                disabled={itemSectionId === null}
                checked={itemValues.openInNewTab}
                onChange={(event) =>
                  setItemValues((current) => ({
                    ...current,
                    openInNewTab: event.target.checked,
                  }))
                }
              />
              در تب جدید باز شود
            </label>
          )}
          <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-600">
            <input
              type="checkbox"
              disabled={itemSectionId === null}
              checked={itemValues.isActive}
              onChange={(event) =>
                setItemValues((current) => ({
                  ...current,
                  isActive: event.target.checked,
                }))
              }
            />
            محتوا فعال باشد
          </label>
          <div className="min-w-0 md:col-span-2">
            <button
              disabled={busy || itemSectionId === null}
              className="rounded-xl bg-secondary-900 px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
            >
              {busy ? "در حال ذخیره..." : editingItem ? "ذخیره محتوا" : "افزودن محتوا"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
