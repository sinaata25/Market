"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ContactIcon from "@/components/layout/ContactIcon";
import { api, type ApiResult } from "@/lib/client-api";
import { CONTACT_ICONS, contactIconName, type FloatingContactButton } from "@/lib/floating-contacts";

type AdminButton = FloatingContactButton & {
  rawUrl: string;
  phoneNumber: string;
  username: string;
  email: string;
  iconId: number | null;
  uploadedIcon: string | null;
  isActive: boolean;
};
type Platform = { value: string; label: string; field: string };
type LibraryIcon = { id: number; name: string; image: string | null };
type Form = {
  title: string; platform: string; phoneNumber: string; username: string; email: string;
  url: string; iconName: string; iconId: string; tooltipText: string;
  position: FloatingContactButton["position"]; displayOrder: string;
  isActive: boolean; openInNewTab: boolean;
};
const API = "/api/admin/floating-contact-buttons";
const INPUT = "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500";
const ACTION = "min-h-11 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 hover:border-brand-400 disabled:opacity-40";
const EMPTY: Form = {
  title: "", platform: "whatsapp", phoneNumber: "", username: "", email: "", url: "",
  iconName: "", iconId: "", tooltipText: "", position: "bottom-right", displayOrder: "0",
  isActive: true, openInNewTab: true,
};

export default function FloatingContactsAdminPage() {
  const router = useRouter();
  const [buttons, setButtons] = useState<AdminButton[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [icons, setIcons] = useState<LibraryIcon[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<AdminButton | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Form>(EMPTY);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const editor = useRef<HTMLFormElement>(null);
  const iconFileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const [result, library] = await Promise.all([
      api.get<{ buttons: AdminButton[]; platforms: Platform[] }>(API),
      api.get<{ icons: LibraryIcon[] }>("/api/admin/footer/icons"),
    ]);
    if (result.ok && result.data) {
      setButtons(result.data.buttons);
      setPlatforms(result.data.platforms);
    } else setError(result.error ?? "دریافت دکمه‌ها ناموفق بود");
    if (library.ok && library.data) setIcons(library.data.icons);
    setLoading(false);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  function failure(result: ApiResult<unknown>) {
    setError(result.error ?? "ذخیره تغییرات ناموفق بود");
    const detail = result.errorData as { fieldErrors?: Record<string, string> } | undefined;
    setFields(detail?.fieldErrors ?? {});
  }

  function edit(button: AdminButton | null) {
    setEditing(button);
    setForm(button ? {
      title: button.title, platform: button.platform, phoneNumber: button.phoneNumber,
      username: button.username, email: button.email, url: button.rawUrl,
      iconName: button.iconName, iconId: button.iconId?.toString() ?? "",
      tooltipText: button.tooltipText, position: button.position,
      displayOrder: button.displayOrder.toString(), isActive: button.isActive,
      openInNewTab: button.openInNewTab,
    } : { ...EMPTY, displayOrder: String(Math.max(-1, ...buttons.map((item) => item.displayOrder)) + 1) });
    setFile(null);
    if (iconFileInput.current) iconFileInput.current.value = "";
    setError("");
    setFields({});
    setMessage("");
    setShowForm(true);
    requestAnimationFrame(() => {
      editor.current?.scrollIntoView({ block: "start" });
      editor.current?.querySelector<HTMLInputElement>("input")?.focus({ preventScroll: true });
    });
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setFields({});
    setMessage("");
    const payload = {
      ...form,
      phoneNumber: destinationField === "phone" ? form.phoneNumber : "",
      username: destinationField === "username" ? form.username : "",
      email: destinationField === "email" ? form.email : "",
      iconId: form.iconId ? Number(form.iconId) : null,
      displayOrder: Number(form.displayOrder),
    };
    const result = editing
      ? await api.patch<{ button: AdminButton }>(`${API}/${editing.id}`, payload)
      : await api.post<{ button: AdminButton }>(API, payload);
    if (!result.ok || !result.data) {
      failure(result);
      setBusy(false);
      return;
    }
    const saved = result.data.button;
    if (file) {
      const body = new FormData();
      body.append("file", file);
      const upload = await api.upload(`${API}/${saved.id}/icon`, body);
      if (!upload.ok) {
        setEditing(saved);
        failure(upload);
        setMessage("اطلاعات دکمه ذخیره شد؛ آیکن آپلود نشد. فایل را اصلاح و دوباره ذخیره کنید.");
        await load();
        router.refresh();
        setBusy(false);
        return;
      }
    }
    setShowForm(false);
    setFile(null);
    await load();
    router.refresh();
    setMessage("دکمه ذخیره شد. تغییرات با تازه‌سازی فروشگاه نمایش داده می‌شود.");
    setBusy(false);
  }

  async function action(button: AdminButton, kind: "toggle" | "delete" | "up" | "down" | "remove-icon") {
    if (kind === "delete" && !window.confirm(`دکمه «${button.title}» حذف شود؟`)) return;
    setBusy(true);
    setError("");
    setMessage("");
    let result: ApiResult<unknown>;
    if (kind === "toggle") result = await api.patch(`${API}/${button.id}`, { isActive: !button.isActive });
    else if (kind === "delete") result = await api.delete(`${API}/${button.id}`);
    else if (kind === "remove-icon") result = await api.delete<{ button: AdminButton }>(`${API}/${button.id}/icon`);
    else result = await api.post(`${API}/${button.id}/move`, { direction: kind });
    if (result.ok) {
      if (kind === "remove-icon" && editing?.id === button.id) {
        setEditing((result.data as { button: AdminButton }).button);
      }
      if (kind === "delete" && editing?.id === button.id) setShowForm(false);
      await load();
      router.refresh();
      setMessage("تغییرات ذخیره شد.");
    } else failure(result);
    setBusy(false);
  }

  function field<K extends keyof Form>(name: K, value: Form[K]) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function textInput(name: "title" | "phoneNumber" | "username" | "email" | "url" | "tooltipText" | "platform", label: string, placeholder = "", ltr = false) {
    return (
      <label className="block text-sm text-slate-600">
        {label}
        <input className={INPUT} value={form[name]} placeholder={placeholder} dir={ltr ? "ltr" : undefined}
          required={name === "title" || name === "platform"} maxLength={name === "title" ? 120 : name === "tooltipText" ? 200 : name === "phoneNumber" || name === "platform" ? 40 : 1000}
          aria-invalid={!!fields[name]} aria-describedby={fields[name] ? `contact-error-${name}` : undefined}
          onChange={(event) => field(name, event.target.value)} />
        {fields[name] && <span id={`contact-error-${name}`} className="mt-1 block text-xs text-red-600">{fields[name]}</span>}
      </label>
    );
  }

  const selectedPlatform = platforms.find((item) => item.value === form.platform);
  const destinationField = selectedPlatform?.field ?? "url";
  const selectedImage = editing?.uploadedIcon || icons.find((icon) => String(icon.id) === form.iconId)?.image || null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-800">دکمه‌های تماس شناور</h1>
          <p className="mt-1 text-sm leading-6 text-slate-500">راه‌های تماس در گوشه‌های فروشگاه؛ ترتیب هر سمت از بالا به پایین است.</p>
        </div>
        <button className="min-h-11 rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-40" disabled={busy || loading} onClick={() => edit(null)}>افزودن دکمه</button>
      </div>
      {error && <div role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {message && <p role="status" className="rounded-xl bg-brand-50 p-3 text-sm text-brand-700">{message}</p>}

      {showForm && (
        <form ref={editor} onSubmit={save} className="scroll-mt-40 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
          <fieldset disabled={busy} className="space-y-5 disabled:opacity-70">
            <legend className="mb-4 font-bold text-slate-800">{editing ? `ویرایش ${editing.title}` : "دکمه جدید"}</legend>
            <div className="grid gap-4 sm:grid-cols-2">
              {textInput("title", "عنوان قابل خواندن برای کاربران")}
              <label className="text-sm text-slate-600">پلتفرم
                <select className={INPUT} value={selectedPlatform ? form.platform : "__other"} onChange={(event) => field("platform", event.target.value === "__other" ? "my-platform" : event.target.value)}>
                  {platforms.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                  <option value="__other">پلتفرم دیگر</option>
                </select>
              </label>
              {!selectedPlatform && textInput("platform", "شناسه پلتفرم (حروف لاتین)", "my-platform", true)}
              {destinationField === "phone" && textInput("phoneNumber", "شماره تماس با کد کشور", "+98 912 345 6789", true)}
              {destinationField === "username" && textInput("username", "نام کاربری یا نشانی کامل", "@username", true)}
              {destinationField === "email" && textInput("email", "نشانی ایمیل", "hello@example.com", true)}
              {textInput("url", "نشانی دلخواه (اولویت با این نشانی است)", "https://example.com", true)}
              {textInput("tooltipText", "متن راهنما (اختیاری)")}
              <label className="text-sm text-slate-600">محل نمایش
                <select className={INPUT} value={form.position} onChange={(event) => field("position", event.target.value as Form["position"])}>
                  <option value="bottom-right">پایین راست</option><option value="bottom-left">پایین چپ</option>
                </select>
              </label>
              <label className="text-sm text-slate-600">ترتیب نمایش (عدد کوچک‌تر بالاتر است)
                <input type="number" min="0" max="2147483647" required step="1" className={INPUT} value={form.displayOrder} onChange={(event) => field("displayOrder", event.target.value)} />
                {fields.displayOrder && <span className="text-xs text-red-600">{fields.displayOrder}</span>}
              </label>
            </div>
            <p className="text-xs leading-6 text-slate-500">برای واتساپ، شماره موبایل ایران با ۰۹ هم پذیرفته می‌شود. نشانی دلخواه می‌تواند پیوند وب، tel:، sms: یا mailto: باشد.</p>
            <div className="rounded-xl bg-slate-50 p-4">
              <div className="mb-4 flex items-center gap-3">
                <span className="grid size-12 shrink-0 place-items-center rounded-full bg-brand-600 text-white"><ContactIcon image={selectedImage} name={contactIconName(form)} /></span>
                <p className="text-sm text-slate-600">اولویت آیکن: فایل آپلودی، کتابخانه، سپس آیکن پیش‌فرض.</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm text-slate-600">آیکن پیش‌فرض
                  <select className={INPUT} value={form.iconName} onChange={(event) => field("iconName", event.target.value)}>
                    <option value="">خودکار بر اساس پلتفرم</option>
                    {Object.entries(CONTACT_ICONS).map(([value, icon]) => <option key={value} value={value}>{icon.label}</option>)}
                  </select>
                </label>
                <label className="text-sm text-slate-600">انتخاب از کتابخانه
                  <select className={INPUT} value={form.iconId} onChange={(event) => field("iconId", event.target.value)}>
                    <option value="">بدون آیکن کتابخانه</option>
                    {icons.map((icon) => <option key={icon.id} value={icon.id}>{icon.name}</option>)}
                  </select>
                </label>
                <label className="text-sm text-slate-600">آپلود آیکن دلخواه
                  <input ref={iconFileInput} key={editing?.id ?? "new"} type="file" accept=".png,.jpg,.jpeg,.webp,.svg" className={`${INPUT} max-w-full`} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
                  <span className="mt-1 block text-xs leading-5 text-slate-500">PNG و SVG ایمن تا ۵ مگابایت؛ JPG و WebP تا ۲ مگابایت.</span>
                  {fields.icon && <span className="text-xs text-red-600">{fields.icon}</span>}
                </label>
                <div className="flex flex-wrap items-center gap-3">
                  {editing?.uploadedIcon && <button type="button" className={ACTION} onClick={() => action(editing, "remove-icon")}>حذف آیکن آپلودی</button>}
                  <Link href="/admin/footer" className="text-xs text-brand-700 underline">مدیریت کتابخانه آیکن‌ها</Link>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-5 text-sm text-slate-600">
              <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={form.isActive} onChange={(event) => field("isActive", event.target.checked)} />فعال و قابل نمایش</label>
              <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={form.openInNewTab} onChange={(event) => field("openInNewTab", event.target.checked)} />باز کردن پیوند وب در تب جدید</label>
            </div>
            <div className="flex gap-3">
              <button type="submit" className="min-h-11 rounded-xl bg-brand-600 px-5 py-2 text-sm font-bold text-white">{busy ? "در حال ذخیره…" : "ذخیره دکمه"}</button>
              <button type="button" className={ACTION} onClick={() => setShowForm(false)}>انصراف</button>
            </div>
          </fieldset>
        </form>
      )}

      {loading ? <p className="p-8 text-center text-sm text-slate-400">در حال بارگذاری…</p> : buttons.length === 0 ? (
        <p className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">هنوز دکمه‌ای تعریف نشده است. با افزودن دکمه، راه تماس را در فروشگاه نمایش دهید.</p>
      ) : ["bottom-right", "bottom-left"].map((position) => {
        const items = buttons.filter((button) => button.position === position);
        if (!items.length) return null;
        return <section key={position} className="space-y-3">
          <h2 className="font-bold text-slate-700">{position === "bottom-right" ? "پایین راست" : "پایین چپ"}</h2>
          {items.map((button, index) => (
            <article key={button.id} className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
              <span className={`grid size-12 shrink-0 place-items-center rounded-full bg-brand-600 text-white ${button.isActive ? "" : "opacity-40"}`}><ContactIcon image={button.icon} name={contactIconName(button)} /></span>
              <div className="min-w-0 flex-1 basis-40">
                <h3 className="font-bold text-slate-800">{button.title} <span className="text-xs font-normal text-slate-400">{button.isActive ? "فعال" : "غیرفعال"}</span></h3>
                <bdi dir="ltr" className="mt-1 block break-all text-xs text-slate-500">{button.url}</bdi>
              </div>
              <div className="flex flex-wrap gap-2">
                <button className={ACTION} aria-label={`انتقال ${button.title} به بالا`} disabled={busy || index === 0} onClick={() => action(button, "up")}>↑</button>
                <button className={ACTION} aria-label={`انتقال ${button.title} به پایین`} disabled={busy || index === items.length - 1} onClick={() => action(button, "down")}>↓</button>
                <button className={ACTION} disabled={busy} onClick={() => action(button, "toggle")}>{button.isActive ? "غیرفعال کردن" : "فعال کردن"}</button>
                <button className={ACTION} disabled={busy} onClick={() => edit(button)}>ویرایش</button>
                <button className={`${ACTION} text-red-600`} disabled={busy} onClick={() => action(button, "delete")}>حذف</button>
              </div>
            </article>
          ))}
        </section>;
      })}
    </div>
  );
}
