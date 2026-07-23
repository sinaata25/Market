"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/client-api";
import { faNum, faDateTime } from "@/components/admin/ui";

type Meta = {
  pageType: string;
  objectKey: string;
  path: string | null;
  metaTitle: string;
  metaDescription: string;
  slug: string;
  canonical: string;
  robotsIndex: boolean;
  robotsFollow: boolean;
  focusKeyword: string;
  ogTitle: string;
  ogDescription: string;
  ogImage: string;
  twitterCard: string;
  schemaType: string;
  schemaCustom: string;
  defaults: { title: string; description: string; image: string };
  effectiveTitle: string;
  effectiveDescription: string;
};

type Revision = {
  id: number;
  createdAt: string;
  user: string;
  data: Record<string, unknown>;
};

// ─── تحلیل سئو (مشابه Yoast) ─────────────────────────────────

type Check = { label: string; pass: boolean; weight: number };

function seoChecks(m: Meta): Check[] {
  const title = m.metaTitle || "";
  const desc = m.metaDescription || "";
  const kw = m.focusKeyword.trim();
  return [
    { label: "عنوان متا تنظیم شده", pass: title.length > 0, weight: 2 },
    {
      label: "طول عنوان بین ۳۰ تا ۶۰ حرف",
      pass: title.length >= 30 && title.length <= 60,
      weight: 2,
    },
    { label: "توضیحات متا تنظیم شده", pass: desc.length > 0, weight: 2 },
    {
      label: "طول توضیحات بین ۷۰ تا ۱۶۰ حرف",
      pass: desc.length >= 70 && desc.length <= 160,
      weight: 2,
    },
    { label: "کلمه کلیدی کانونی تعیین شده", pass: kw.length > 0, weight: 1 },
    {
      label: "کلمه کلیدی در عنوان",
      pass: Boolean(kw) && title.includes(kw),
      weight: 2,
    },
    {
      label: "کلمه کلیدی در توضیحات",
      pass: Boolean(kw) && desc.includes(kw),
      weight: 1,
    },
    {
      label: "صفحه قابل ایندکس است",
      pass: m.robotsIndex,
      weight: 1,
    },
    {
      label: "تصویر اشتراک‌گذاری (OG) دارد",
      pass: Boolean(m.ogImage || m.defaults.image),
      weight: 1,
    },
  ];
}

function seoScore(checks: Check[]): number {
  const total = checks.reduce((s, c) => s + c.weight, 0);
  const passed = checks
    .filter((c) => c.pass)
    .reduce((s, c) => s + c.weight, 0);
  return Math.round((passed / total) * 100);
}

// خوانایی ساده: میانگین طول جمله + تعداد کلمات
function readability(text: string) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const sentences = text
    .split(/[.!؟?۔\n]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const avg = sentences.length ? words.length / sentences.length : 0;
  let label = "—";
  let cls = "text-slate-400";
  if (words.length > 0) {
    if (avg <= 15) {
      label = "روان و خوانا";
      cls = "text-emerald-600";
    } else if (avg <= 25) {
      label = "متوسط";
      cls = "text-amber-600";
    } else {
      label = "جملات طولانی — سخت‌خوان";
      cls = "text-red-500";
    }
  }
  return { words: words.length, avg: Math.round(avg), label, cls };
}

function inputCls() {
  return "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";
}

function SeoEditorInner() {
  const sp = useSearchParams();
  const type = sp.get("type") ?? "";
  const key = sp.get("key") ?? "";
  const qs = `type=${type}&key=${encodeURIComponent(key)}`;

  const [meta, setMeta] = useState<Meta | null>(null);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [showRevisions, setShowRevisions] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(
    null
  );
  const [slugWarning, setSlugWarning] = useState("");
  const [initialSlug, setInitialSlug] = useState("");

  useEffect(() => {
    api.get<{ meta: Meta }>(`/api/admin/seo/meta?${qs}`).then((res) => {
      if (res.ok && res.data) {
        setMeta(res.data.meta);
        setInitialSlug(res.data.meta.slug);
      }
    });
  }, [qs]);

  function set<K extends keyof Meta>(field: K, value: Meta[K]) {
    setMeta((m) => (m ? { ...m, [field]: value } : m));
    if (field === "slug" && meta) {
      setSlugWarning(
        initialSlug && value !== initialSlug
          ? "⚠️ با تغییر نامک، ریدایرکت ۳۰۱ از آدرس قبلی به آدرس جدید به‌صورت خودکار ثبت می‌شود."
          : ""
      );
    }
  }

  async function save() {
    if (!meta) return;
    setSaving(true);
    setMessage(null);
    const res = await api.put<{
      meta: Meta;
      autoRedirect: { from: string; to: string } | null;
    }>(`/api/admin/seo/meta?${qs}`, {
      metaTitle: meta.metaTitle,
      metaDescription: meta.metaDescription,
      slug: meta.slug,
      canonical: meta.canonical,
      robotsIndex: meta.robotsIndex,
      robotsFollow: meta.robotsFollow,
      focusKeyword: meta.focusKeyword,
      ogTitle: meta.ogTitle,
      ogDescription: meta.ogDescription,
      ogImage: meta.ogImage,
      twitterCard: meta.twitterCard,
      schemaType: meta.schemaType,
      schemaCustom: meta.schemaCustom,
    });
    setSaving(false);
    if (!res.ok || !res.data) {
      setMessage({ ok: false, text: res.error ?? "خطا در ذخیره" });
      return;
    }
    setMeta(res.data.meta);
    setInitialSlug(res.data.meta.slug);
    setSlugWarning("");
    setMessage({
      ok: true,
      text: res.data.autoRedirect
        ? `ذخیره شد ✅ — ریدایرکت خودکار: ${res.data.autoRedirect.from} ← ${res.data.autoRedirect.to}`
        : "ذخیره شد ✅",
    });
  }

  async function loadRevisions() {
    const res = await api.get<{ revisions: Revision[] }>(
      `/api/admin/seo/revisions?${qs}`
    );
    if (res.ok && res.data) setRevisions(res.data.revisions);
    setShowRevisions(true);
  }

  async function restore(rev: Revision) {
    if (!confirm("این نسخه بازگردانی شود؟")) return;
    const res = await api.post<{ meta: Meta }>(
      `/api/admin/seo/revisions?${qs}`,
      { revisionId: rev.id }
    );
    if (res.ok && res.data) {
      setMeta(res.data.meta);
      setShowRevisions(false);
      setMessage({ ok: true, text: "نسخه بازگردانی شد ✅" });
    }
  }

  if (!meta) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  const checks = seoChecks(meta);
  const score = seoScore(checks);
  const scoreColor =
    score >= 80
      ? "text-emerald-600"
      : score >= 50
        ? "text-amber-600"
        : "text-red-500";
  const read = readability(meta.metaDescription);
  const serpTitle = meta.metaTitle || meta.defaults.title;
  const serpDesc = meta.metaDescription || meta.defaults.description;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href="/admin/seo/pages"
            className="text-xs text-slate-400 hover:text-brand-600"
          >
            → متای صفحات
          </Link>
          <h1 className="mt-1 text-lg font-bold text-slate-800">
            ویرایش سئو:{" "}
            <code dir="ltr" className="text-sm text-brand-600">
              {meta.path}
            </code>
          </h1>
        </div>
        <button
          onClick={loadRevisions}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs text-slate-600 transition hover:border-brand-400"
        >
          🕓 تاریخچه نسخه‌ها
        </button>
      </div>

      {/* پیش‌نمایش گوگل */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5">
        <h2 className="mb-3 text-xs font-bold text-slate-500">
          پیش‌نمایش نتیجه گوگل (SERP)
        </h2>
        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-4">
          <p className="mb-0.5 text-xs text-emerald-700" dir="ltr">
            localhost:3000{meta.path}
          </p>
          <p className="mb-1 truncate text-base text-blue-700 hover:underline">
            {serpTitle}
          </p>
          <p className="line-clamp-2 text-xs leading-5 text-slate-500">
            {serpDesc}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* فرم اصلی */}
        <div className="space-y-4 lg:col-span-2">
          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="text-xs font-medium text-slate-600">
                  عنوان متا (Meta Title)
                </label>
                <Counter len={meta.metaTitle.length} min={30} max={60} />
              </div>
              <input
                value={meta.metaTitle}
                onChange={(e) => set("metaTitle", e.target.value)}
                placeholder={meta.defaults.title}
                className={inputCls()}
              />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="text-xs font-medium text-slate-600">
                  توضیحات متا (Meta Description)
                </label>
                <Counter
                  len={meta.metaDescription.length}
                  min={70}
                  max={160}
                />
              </div>
              <textarea
                rows={3}
                value={meta.metaDescription}
                onChange={(e) => set("metaDescription", e.target.value)}
                placeholder={meta.defaults.description}
                className={`${inputCls()} resize-none leading-6`}
              />
              <p className="mt-1 text-[11px] text-slate-400">
                <span className="font-num">{faNum(read.words)}</span> کلمه —
                خوانایی: <span className={read.cls}>{read.label}</span>
              </p>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                کلمه کلیدی کانونی (Focus Keyword)
              </label>
              <input
                value={meta.focusKeyword}
                onChange={(e) => set("focusKeyword", e.target.value)}
                placeholder="مثلا: اره موتوری"
                className={inputCls()}
              />
            </div>
          </div>

          {/* URL و ایندکس */}
          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="text-xs font-bold text-slate-500">URL و ایندکس</h2>
            {meta.pageType === "product" && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  نامک (Slug)
                </label>
                <input
                  dir="ltr"
                  value={meta.slug}
                  onChange={(e) => set("slug", e.target.value)}
                  placeholder="masalan: chainsaw-52cc"
                  className={inputCls()}
                />
                {slugWarning && (
                  <p className="mt-1.5 rounded-lg bg-amber-50 px-3 py-2 text-[11px] leading-5 text-amber-700">
                    {slugWarning}
                  </p>
                )}
                {meta.slug && (
                  <p className="mt-1 text-[11px] text-slate-400" dir="ltr">
                    /product/{meta.slug}
                  </p>
                )}
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                Canonical URL (اختیاری)
              </label>
              <input
                dir="ltr"
                value={meta.canonical}
                onChange={(e) => set("canonical", e.target.value)}
                placeholder="https://example.com/page"
                className={inputCls()}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  Robots — ایندکس
                </label>
                <select
                  value={meta.robotsIndex ? "index" : "noindex"}
                  onChange={(e) =>
                    set("robotsIndex", e.target.value === "index")
                  }
                  className={inputCls()}
                >
                  <option value="index">index</option>
                  <option value="noindex">noindex</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  Robots — فالو
                </label>
                <select
                  value={meta.robotsFollow ? "follow" : "nofollow"}
                  onChange={(e) =>
                    set("robotsFollow", e.target.value === "follow")
                  }
                  className={inputCls()}
                >
                  <option value="follow">follow</option>
                  <option value="nofollow">nofollow</option>
                </select>
              </div>
            </div>
          </div>

          {/* شبکه‌های اجتماعی */}
          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="text-xs font-bold text-slate-500">
              اشتراک‌گذاری — Open Graph و Twitter
            </h2>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                عنوان OG
              </label>
              <input
                value={meta.ogTitle}
                onChange={(e) => set("ogTitle", e.target.value)}
                placeholder="در صورت خالی بودن، عنوان متا استفاده می‌شود"
                className={inputCls()}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                توضیحات OG
              </label>
              <textarea
                rows={2}
                value={meta.ogDescription}
                onChange={(e) => set("ogDescription", e.target.value)}
                className={`${inputCls()} resize-none`}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  تصویر OG (آدرس)
                </label>
                <input
                  dir="ltr"
                  value={meta.ogImage}
                  onChange={(e) => set("ogImage", e.target.value)}
                  placeholder="/media/products/p1.jpg"
                  className={inputCls()}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">
                  Twitter Card
                </label>
                <select
                  value={meta.twitterCard}
                  onChange={(e) => set("twitterCard", e.target.value)}
                  className={inputCls()}
                >
                  <option value="summary_large_image">
                    summary_large_image
                  </option>
                  <option value="summary">summary</option>
                </select>
              </div>
            </div>
          </div>

          {/* اسکیما */}
          <div className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5">
            <h2 className="text-xs font-bold text-slate-500">
              داده ساختاریافته (Schema)
            </h2>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                نوع اسکیما
              </label>
              <select
                value={meta.schemaType}
                onChange={(e) => set("schemaType", e.target.value)}
                className={inputCls()}
              >
                <option value="">خودکار (بر اساس نوع صفحه)</option>
                <option value="Product">Product</option>
                <option value="Article">Article</option>
                <option value="FAQPage">FAQPage</option>
                <option value="WebPage">WebPage</option>
                <option value="CollectionPage">CollectionPage</option>
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                JSON-LD سفارشی (اختیاری — جایگزین اسکیمای خودکار)
              </label>
              <textarea
                dir="ltr"
                rows={4}
                value={meta.schemaCustom}
                onChange={(e) => set("schemaCustom", e.target.value)}
                placeholder='{"@context": "https://schema.org", ...}'
                className={`${inputCls()} resize-none font-mono text-xs`}
              />
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

          <button
            onClick={save}
            disabled={saving}
            className="rounded-xl bg-brand-600 px-8 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {saving ? "در حال ذخیره..." : "ذخیره تغییرات سئو"}
          </button>
        </div>

        {/* ستون امتیاز */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-100 bg-white p-5 lg:sticky lg:top-24">
            <h2 className="mb-3 text-xs font-bold text-slate-500">
              امتیاز سئوی صفحه
            </h2>
            <p className={`mb-4 text-center text-4xl font-bold font-num ${scoreColor}`}>
              {faNum(score)}
              <span className="text-base">٪</span>
            </p>
            <div className="mb-4 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all ${
                  score >= 80
                    ? "bg-emerald-500"
                    : score >= 50
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${score}%` }}
              />
            </div>
            <ul className="space-y-2">
              {checks.map((c) => (
                <li
                  key={c.label}
                  className="flex items-start gap-2 text-[11px] leading-5"
                >
                  <span>{c.pass ? "✅" : "❌"}</span>
                  <span className={c.pass ? "text-slate-600" : "text-slate-400"}>
                    {c.label}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* تاریخچه نسخه‌ها */}
      {showRevisions && (
        <div className="rounded-2xl border border-slate-100 bg-white p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-700">
              🕓 تاریخچه نسخه‌ها
            </h2>
            <button
              onClick={() => setShowRevisions(false)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              بستن ✕
            </button>
          </div>
          {revisions.length === 0 ? (
            <p className="py-6 text-center text-xs text-slate-400">
              هنوز نسخه‌ای ثبت نشده است
            </p>
          ) : (
            <ul className="divide-y divide-slate-50">
              {revisions.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between gap-3 py-3 text-xs"
                >
                  <div className="min-w-0">
                    <p className="text-slate-600">
                      {String(r.data.meta_title || "(بدون عنوان)")}
                    </p>
                    <p className="mt-0.5 text-[11px] text-slate-400 font-num">
                      {faDateTime(r.createdAt)} — {r.user}
                    </p>
                  </div>
                  <button
                    onClick={() => restore(r)}
                    className="shrink-0 rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] text-slate-600 transition hover:border-brand-400 hover:text-brand-700"
                  >
                    بازگردانی
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function Counter({ len, min, max }: { len: number; min: number; max: number }) {
  const cls =
    len === 0
      ? "text-slate-300"
      : len >= min && len <= max
        ? "text-emerald-600"
        : "text-amber-600";
  return (
    <span className={`text-[11px] font-num ${cls}`}>
      {faNum(len)} / {faNum(max)}
    </span>
  );
}

export default function SeoEditorPage() {
  return (
    <Suspense
      fallback={
        <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
          در حال بارگذاری...
        </div>
      }
    >
      <SeoEditorInner />
    </Suspense>
  );
}
