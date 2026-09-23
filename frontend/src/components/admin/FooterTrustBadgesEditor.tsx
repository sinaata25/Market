"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, type ApiResult } from "@/lib/client-api";
import { type FooterTrustBadge } from "@/lib/footer-trust-badges";

type Badge = FooterTrustBadge & { isActive: boolean };
type Section = { id: number; isActive: boolean; items: Badge[] };
type Values = { label: string; url: string; altText: string; position: string; isActive: boolean; openInNewTab: boolean };
const EMPTY: Values = { label: "", url: "", altText: "", position: "0", isActive: true, openInNewTab: true };
const INPUT = "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-brand-500";
const ACTION = "min-h-11 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 hover:border-brand-400 disabled:opacity-40";

function BadgePreview({ file, saved }: { file: File | null; saved: string | null }) {
  const preview = useMemo(() => file ? URL.createObjectURL(file) : null, [file]);
  useEffect(() => {
    if (preview) return () => URL.revokeObjectURL(preview);
  }, [preview]);
  const src = preview ?? saved;
  if (!src) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="پیش‌نمایش نماد" width={96} height={96} className="size-24 rounded-xl border border-slate-100 bg-white p-2 object-contain" />;
}

export default function FooterTrustBadgesEditor({ section, loading, onChanged }: {
  section?: Section; loading: boolean; onChanged: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<Badge | null>(null);
  const [opened, setOpened] = useState(false);
  const [values, setValues] = useState<Values>(EMPTY);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const form = useRef<HTMLFormElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const items = [...(section?.items ?? [])].filter((item) => item.type === "badge").sort((a, b) => a.position - b.position || a.id - b.id);

  function showErrors(result: ApiResult<unknown>) {
    setError(result.error ?? "ذخیره نماد انجام نشد");
    const data = result.errorData as { fieldErrors?: Record<string, string | string[]> } | undefined;
    setFields(Object.fromEntries(Object.entries(data?.fieldErrors ?? {}).map(([key, value]) => [key, Array.isArray(value) ? value[0] : value])));
  }

  function edit(badge: Badge | null) {
    setEditing(badge);
    setValues(badge ? {
      label: badge.label ?? "", url: badge.url ?? "", altText: badge.altText ?? "",
      position: String(badge.position), isActive: badge.isActive, openInNewTab: badge.openInNewTab,
    } : { ...EMPTY, position: String(Math.max(-1, ...items.map((item) => item.position)) + 1) });
    setFile(null);
    if (fileInput.current) fileInput.current.value = "";
    setError(""); setMessage(""); setFields({}); setOpened(true);
    requestAnimationFrame(() => form.current?.querySelector<HTMLInputElement>("input")?.focus());
  }

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (!editing && !file) {
      setError("تصویر نماد را انتخاب کنید");
      setFields({ image: "تصویر نماد الزامی است" });
      return;
    }
    setBusy(true); setError(""); setMessage(""); setFields({});
    const body = new FormData();
    Object.entries(values).forEach(([key, value]) => body.append(key, String(value)));
    if (file) body.append("file", file);
    const result = await api.upload(`/api/admin/footer/trust-badges${editing ? `/${editing.id}` : ""}`, body);
    if (result.ok) {
      setOpened(false); setFile(null);
      await onChanged();
      setMessage("نماد ذخیره شد. تغییرات با تازه‌سازی فروشگاه نمایش داده می‌شود.");
    } else showErrors(result);
    setBusy(false);
  }

  async function action(badge: Badge, kind: "toggle" | "delete" | "up" | "down") {
    if (busy || (kind === "delete" && !window.confirm(`نماد «${badge.label}» حذف شود؟`))) return;
    setBusy(true); setError(""); setMessage("");
    const url = `/api/admin/footer/items/${badge.id}`;
    const result = kind === "toggle" ? await api.patch(url, { isActive: !badge.isActive })
      : kind === "delete" ? await api.delete(url)
      : await api.post(`${url}/move`, { direction: kind });
    if (result.ok) {
      if (editing?.id === badge.id) setOpened(false);
      await onChanged();
      setMessage("تغییرات نماد ذخیره شد.");
    } else showErrors(result);
    setBusy(false);
  }

  async function toggleSection() {
    if (!section || busy) return;
    setBusy(true); setError(""); setMessage("");
    const result = await api.patch(`/api/admin/footer/sections/${section.id}`, { isActive: !section.isActive });
    if (result.ok) await onChanged(); else showErrors(result);
    setBusy(false);
  }

  return (
    <section id="footer-trust-badges" className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-bold text-slate-700">نمادها و مجوزها</h2>
          <p className="mt-1 text-xs leading-6 text-slate-500">نماد اعتماد الکترونیکی و سایر مجوزهای فروشگاه؛ نمایش به ترتیب از عدد کوچک‌تر.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {section && <button type="button" disabled={busy} onClick={toggleSection} className={ACTION}>{section.isActive ? "پنهان کردن بخش" : "نمایش بخش"}</button>}
          <button type="button" disabled={busy || loading} onClick={() => edit(null)} className="min-h-11 rounded-xl bg-brand-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-40">افزودن نماد</button>
        </div>
      </div>
      {section?.isActive === false && <p className="mt-3 text-sm text-amber-700">این بخش در فروشگاه پنهان است؛ برای نمایش نمادها «نمایش بخش» را بزنید.</p>}
      {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {message && <p role="status" className="mt-4 rounded-xl bg-brand-50 p-3 text-sm text-brand-700">{message}</p>}

      {opened && <form ref={form} onSubmit={save} className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <fieldset disabled={busy} className="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 disabled:opacity-60">
          <legend className="mb-4 font-bold text-slate-700">{editing ? "ویرایش نماد" : "نماد جدید"}</legend>
          {([ ["label", "عنوان نماد", "نماد اعتماد الکترونیکی", 120], ["url", "لینک استعلام یا مقصد", "https://...", 300], ["altText", "متن جایگزین تصویر (اختیاری)", "خالی = عنوان نماد", 200] ] as const).map(([key, label, placeholder, max]) => <label key={key} className="min-w-0 text-sm text-slate-600">
            {label}
            <input value={values[key]} required={key !== "altText"} type={key === "url" ? "url" : "text"} dir={key === "url" ? "ltr" : undefined} maxLength={max} placeholder={placeholder} className={INPUT}
              aria-invalid={!!fields[key]} aria-describedby={fields[key] ? `badge-error-${key}` : undefined}
              onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))} />
            {fields[key] && <span id={`badge-error-${key}`} className="mt-1 block text-xs text-red-600">{fields[key]}</span>}
          </label>)}
          <label className="min-w-0 text-sm text-slate-600">ترتیب نمایش
            <input type="number" min="0" max="2147483647" step="1" required value={values.position} className={INPUT} onChange={(event) => setValues((current) => ({ ...current, position: event.target.value }))} />
          </label>
          <div className="min-w-0 space-y-2 sm:col-span-2">
            <label className="block text-sm text-slate-600">تصویر نماد
              <input ref={fileInput} type="file" required={!editing} accept=".png,.jpg,.jpeg,.webp,.svg" className={INPUT} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            </label>
            <p className="text-xs leading-6 text-slate-500">PNG، JPG و WebP تا ۲ مگابایت؛ SVG ایمن تا ۵ مگابایت. برای جایگزینی تصویر، فایل تازه انتخاب کنید.</p>
            {(fields.image || fields.file) && <p className="text-xs text-red-600">{fields.image || fields.file}</p>}
            <BadgePreview file={file} saved={editing?.image ?? null} />
          </div>
          <p className="text-xs leading-6 text-slate-500 sm:col-span-2">برای اینماد، تصویر نماد و لینک استعلام اختصاصی فروشگاه را از حساب اینماد خود وارد کنید. کد HTML یا اسکریپت در این بخش اجرا نمی‌شود.</p>
          <label className="flex min-h-11 items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={values.isActive} onChange={(event) => setValues((current) => ({ ...current, isActive: event.target.checked }))} />نماد فعال باشد</label>
          <label className="flex min-h-11 items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={values.openInNewTab} onChange={(event) => setValues((current) => ({ ...current, openInNewTab: event.target.checked }))} />در تب جدید باز شود</label>
          <div className="flex flex-wrap gap-3 sm:col-span-2">
            <button className="min-h-11 rounded-xl bg-brand-600 px-5 py-2 text-sm font-bold text-white">{busy ? "در حال ذخیره…" : "ذخیره نماد"}</button>
            <button type="button" className={ACTION} onClick={() => setOpened(false)}>انصراف</button>
          </div>
        </fieldset>
      </form>}

      {loading ? <p className="p-6 text-center text-sm text-slate-400">در حال دریافت نمادها…</p> : items.length === 0 ? <p className="p-6 text-center text-sm text-slate-400">هنوز نمادی ثبت نشده است. بخش نمادها تا افزودن یک نماد فعال در فروشگاه نمایش داده نمی‌شود.</p> : <ul className="mt-5 divide-y divide-slate-100">
        {items.map((badge, index) => <li key={badge.id} className="flex flex-wrap items-center gap-3 py-4">
          {badge.image && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={badge.image} alt={badge.altText || badge.label || "نماد"} width={64} height={64} className="size-16 shrink-0 rounded-xl border border-slate-100 bg-white p-2 object-contain" />
          )}
          <div className="min-w-0 flex-1 basis-44">
            <h3 className="text-sm font-bold text-slate-800">{badge.label}</h3>
            <p className="mt-1 text-xs text-slate-500">{badge.isActive ? "فعال" : "غیرفعال"} · ترتیب {badge.position.toLocaleString("fa-IR")}</p>
            <bdi dir="ltr" className="mt-1 block break-all text-xs text-slate-500">{badge.url}</bdi>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={busy || index === 0} aria-label={`انتقال ${badge.label} به بالا`} className={ACTION} onClick={() => action(badge, "up")}>↑</button>
            <button type="button" disabled={busy || index === items.length - 1} aria-label={`انتقال ${badge.label} به پایین`} className={ACTION} onClick={() => action(badge, "down")}>↓</button>
            <button type="button" disabled={busy} className={ACTION} onClick={() => edit(badge)}>ویرایش</button>
            <button type="button" disabled={busy} className={ACTION} onClick={() => action(badge, "toggle")}>{badge.isActive ? "غیرفعال کردن" : "فعال کردن"}</button>
            <button type="button" disabled={busy} className={`${ACTION} text-red-600`} onClick={() => action(badge, "delete")}>حذف</button>
          </div>
        </li>)}
      </ul>}
    </section>
  );
}
