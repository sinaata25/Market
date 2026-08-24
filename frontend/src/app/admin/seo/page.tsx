"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { StatCard, faNum } from "@/components/admin/ui";

type Overview = {
  pagesTotal: number;
  missingMeta: number;
  noindexPages: number;
  redirects: number;
  notFoundTotal: number;
  notFoundTop: { path: string; hits: number }[];
  missingAlt: number;
  brokenLinks: number;
  lastScan: string | null;
};

export default function SeoOverview() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Overview>("/api/admin/seo/overview").then((res) => {
      if (res.ok && res.data) setData(res.data);
      else setError(res.error ?? "خطا در دریافت اطلاعات");
    });
  }, []);

  if (error) {
    return (
      <div className="rounded-2xl bg-red-50 p-6 text-center text-sm text-red-500">
        {error}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  const issues = [
    {
      count: data.missingMeta,
      label: "صفحه بدون عنوان متا",
      href: "/admin/seo/pages",
      icon: "📝",
    },
    {
      count: data.missingAlt,
      label: "تصویر بدون Alt",
      href: "/admin/seo/images",
      icon: "🖼️",
    },
    {
      count: data.notFoundTotal,
      label: "مسیر با خطای ۴۰۴",
      href: "/admin/seo/404s",
      icon: "🚫",
    },
    {
      count: data.brokenLinks,
      label: "لینک شکسته در آخرین اسکن",
      href: "/admin/seo/reports",
      icon: "🔗",
    },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">🎯 نمای کلی سئو</h1>
        <div className="flex gap-2 text-xs">
          <a
            href="/sitemap.xml"
            target="_blank"
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-slate-600 transition hover:border-brand-400"
          >
            sitemap.xml ↗
          </a>
          <a
            href="/robots.txt"
            target="_blank"
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-slate-600 transition hover:border-brand-400"
          >
            robots.txt ↗
          </a>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          icon="📄"
          label="کل صفحات سایت"
          value={faNum(data.pagesTotal)}
          accent="bg-blue-50 text-blue-600"
        />
        <StatCard
          icon="↪️"
          label="ریدایرکت فعال"
          value={faNum(data.redirects)}
          accent="bg-violet-50 text-violet-600"
        />
        <StatCard
          icon="🙈"
          label="صفحات noindex"
          value={faNum(data.noindexPages)}
          accent="bg-slate-100 text-slate-600"
        />
        <StatCard
          icon="⏱️"
          label="آخرین اسکن"
          value={
            data.lastScan
              ? new Date(data.lastScan).toLocaleDateString("fa-IR")
              : "—"
          }
          accent="bg-amber-50 text-amber-600"
        />
      </div>

      {/* مشکلات نیازمند رسیدگی */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5">
        <h2 className="mb-4 text-sm font-bold text-slate-700">
          ⚠️ نیازمند رسیدگی
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {issues.map((issue) => (
            <Link
              key={issue.label}
              href={issue.href}
              className={`flex items-center gap-3 rounded-xl border p-4 transition hover:shadow-sm ${
                issue.count > 0
                  ? "border-amber-100 bg-amber-50/50"
                  : "border-slate-100 bg-slate-50/50"
              }`}
            >
              <span className="text-2xl">{issue.icon}</span>
              <div className="flex-1">
                <p
                  className={`text-lg font-bold font-num ${
                    issue.count > 0 ? "text-amber-600" : "text-emerald-600"
                  }`}
                >
                  {faNum(issue.count)}
                </p>
                <p className="text-xs text-slate-500">{issue.label}</p>
              </div>
              <span className="text-xs text-slate-300">←</span>
            </Link>
          ))}
        </div>
      </div>

      {/* پربازدیدترین ۴۰۴ ها */}
      {data.notFoundTop.length > 0 && (
        <div className="rounded-2xl border border-slate-100 bg-white p-5">
          <h2 className="mb-3 text-sm font-bold text-slate-700">
            پربازدیدترین خطاهای ۴۰۴
          </h2>
          <ul className="space-y-2">
            {data.notFoundTop.map((n) => (
              <li
                key={n.path}
                className="flex items-center justify-between text-xs"
              >
                <code dir="ltr" className="text-slate-600">
                  {n.path}
                </code>
                <span className="rounded-md bg-red-50 px-2 py-0.5 font-bold text-red-500 font-num">
                  {faNum(n.hits)} بار
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
