"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/client-api";

type Settings = {
  siteName: string;
  siteUrl: string;
  defaultMetaDescription: string;
  robotsTxt: string;
  sitemapEnabled: boolean;
  sitemapIncludeProducts: boolean;
  sitemapIncludeCategories: boolean;
  sitemapIncludeStatic: boolean;
  sitemapExcludedPaths: string;
  breadcrumbsEnabled: boolean;
  lazyloadEnabled: boolean;
  imageCompressionEnabled: boolean;
  orgSchemaEnabled: boolean;
  hreflang: { lang: string; url: string }[];
};

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";

function Toggle({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between gap-3 rounded-xl border border-slate-100 px-4 py-3 text-right transition hover:border-slate-200"
    >
      <span>
        <span className="block text-xs font-medium text-slate-700">
          {label}
        </span>
        {hint && (
          <span className="mt-0.5 block text-[11px] text-slate-400">
            {hint}
          </span>
        )}
      </span>
      <span
        className={`relative h-5 w-9 shrink-0 rounded-full transition ${
          checked ? "bg-brand-600" : "bg-slate-300"
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
            checked ? "right-0.5" : "right-4.5"
          }`}
        />
      </span>
    </button>
  );
}

export default function SeoSettingsPage() {
  const [s, setS] = useState<Settings | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(
    null
  );

  useEffect(() => {
    api.get<{ settings: Settings }>("/api/admin/seo/settings").then((res) => {
      if (res.ok && res.data) setS(res.data.settings);
    });
  }, []);

  function set<K extends keyof Settings>(key: K, value: Settings[K]) {
    setS((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function save() {
    if (!s) return;
    setSaving(true);
    setMessage(null);
    const res = await api.put<{ settings: Settings }>(
      "/api/admin/seo/settings",
      s
    );
    setSaving(false);
    if (res.ok && res.data) {
      setS(res.data.settings);
      setMessage({ ok: true, text: "تنظیمات ذخیره شد ✅" });
    } else {
      setMessage({ ok: false, text: res.error ?? "خطا در ذخیره" });
    }
  }

  if (!s) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">⚙️ تنظیمات سئو</h1>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* اطلاعات سایت */}
        <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="text-xs font-bold text-slate-500">اطلاعات سایت</h2>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              نام سایت
            </label>
            <input
              value={s.siteName}
              onChange={(e) => set("siteName", e.target.value)}
              className={inputCls}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              آدرس سایت
            </label>
            <input
              dir="ltr"
              value={s.siteUrl}
              onChange={(e) => set("siteUrl", e.target.value)}
              className={inputCls}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              توضیحات متای پیش‌فرض
            </label>
            <textarea
              rows={2}
              value={s.defaultMetaDescription}
              onChange={(e) => set("defaultMetaDescription", e.target.value)}
              className={`${inputCls} resize-none`}
            />
          </div>
        </div>

        {/* قابلیت‌ها */}
        <div className="space-y-2 rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="mb-3 text-xs font-bold text-slate-500">قابلیت‌ها</h2>
          <Toggle
            checked={s.breadcrumbsEnabled}
            onChange={(v) => set("breadcrumbsEnabled", v)}
            label="بردکرامب + اسکیمای BreadcrumbList"
            hint="نمایش مسیر راهنما و داده ساختاریافته آن"
          />
          <Toggle
            checked={s.lazyloadEnabled}
            onChange={(v) => set("lazyloadEnabled", v)}
            label="لیزی‌لود تصاویر"
            hint="بارگذاری تنبل تصاویر برای سرعت بیشتر"
          />
          <Toggle
            checked={s.imageCompressionEnabled}
            onChange={(v) => set("imageCompressionEnabled", v)}
            label="فشرده‌سازی تصاویر هنگام آپلود"
          />
          <Toggle
            checked={s.orgSchemaEnabled}
            onChange={(v) => set("orgSchemaEnabled", v)}
            label="اسکیمای Organization در صفحه اصلی"
          />
        </div>

        {/* سایت‌مپ */}
        <div className="space-y-2 rounded-2xl border border-slate-100 bg-white p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-500">
              نقشه سایت (XML Sitemap)
            </h2>
            <a
              href="/sitemap.xml"
              target="_blank"
              className="text-[11px] text-brand-600 hover:underline"
            >
              مشاهده ↗
            </a>
          </div>
          <Toggle
            checked={s.sitemapEnabled}
            onChange={(v) => set("sitemapEnabled", v)}
            label="سایت‌مپ فعال"
          />
          <Toggle
            checked={s.sitemapIncludeProducts}
            onChange={(v) => set("sitemapIncludeProducts", v)}
            label="شامل محصولات"
          />
          <Toggle
            checked={s.sitemapIncludeCategories}
            onChange={(v) => set("sitemapIncludeCategories", v)}
            label="شامل دسته‌بندی‌ها"
          />
          <Toggle
            checked={s.sitemapIncludeStatic}
            onChange={(v) => set("sitemapIncludeStatic", v)}
            label="شامل صفحات ثابت"
          />
          <div className="pt-2">
            <label className="mb-1.5 block text-xs font-medium text-slate-600">
              مسیرهای حذف‌شده (هر مسیر در یک خط)
            </label>
            <textarea
              dir="ltr"
              rows={3}
              value={s.sitemapExcludedPaths}
              onChange={(e) => set("sitemapExcludedPaths", e.target.value)}
              placeholder={"/cart\n/login"}
              className={`${inputCls} resize-none font-mono text-xs`}
            />
          </div>
        </div>

        {/* hreflang */}
        <div className="rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="mb-3 text-xs font-bold text-slate-500">
            Hreflang (چندزبانه)
          </h2>
          <div className="space-y-2">
            {s.hreflang.map((h, i) => (
              <div key={i} className="flex gap-2">
                <input
                  dir="ltr"
                  value={h.lang}
                  onChange={(e) => {
                    const list = [...s.hreflang];
                    list[i] = { ...list[i], lang: e.target.value };
                    set("hreflang", list);
                  }}
                  placeholder="fa-IR"
                  className={`${inputCls} w-24 text-xs`}
                />
                <input
                  dir="ltr"
                  value={h.url}
                  onChange={(e) => {
                    const list = [...s.hreflang];
                    list[i] = { ...list[i], url: e.target.value };
                    set("hreflang", list);
                  }}
                  placeholder="https://example.com"
                  className={`${inputCls} flex-1 text-xs`}
                />
                <button
                  onClick={() =>
                    set(
                      "hreflang",
                      s.hreflang.filter((_, j) => j !== i)
                    )
                  }
                  className="shrink-0 text-red-400 hover:text-red-600"
                >
                  🗑
                </button>
              </div>
            ))}
          </div>
          <button
            onClick={() =>
              set("hreflang", [...s.hreflang, { lang: "", url: "" }])
            }
            className="mt-3 w-full rounded-xl border border-dashed border-slate-300 py-2 text-xs text-slate-500 transition hover:border-brand-400 hover:text-brand-700"
          >
            + افزودن زبان
          </button>
        </div>
      </div>

      {/* robots.txt */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-500">robots.txt</h2>
          <a
            href="/robots.txt"
            target="_blank"
            className="text-[11px] text-brand-600 hover:underline"
          >
            مشاهده ↗
          </a>
        </div>
        <textarea
          dir="ltr"
          rows={8}
          value={s.robotsTxt}
          onChange={(e) => set("robotsTxt", e.target.value)}
          className={`${inputCls} resize-y font-mono text-xs leading-6`}
        />
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

      <button
        onClick={save}
        disabled={saving}
        className="action-btn rounded-xl bg-brand-600 px-8 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
      >
        {saving ? "در حال ذخیره..." : "ذخیره تنظیمات"}
      </button>
    </div>
  );
}
