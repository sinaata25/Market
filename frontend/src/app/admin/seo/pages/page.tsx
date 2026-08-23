"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { faNum, EmptyRow } from "@/components/admin/ui";

type PageRow = {
  pageType: string;
  objectKey: string;
  title: string;
  path: string;
  hasMeta: boolean;
  titleLength: number;
  descriptionLength: number;
  focusKeyword: string;
  robotsIndex: boolean;
  slug: string;
};

const TYPE_FA: Record<string, string> = {
  static: "صفحه ثابت",
  category: "دسته‌بندی",
  product: "محصول",
};

function statusOf(p: PageRow): { label: string; className: string } {
  if (!p.robotsIndex)
    return { label: "noindex", className: "bg-slate-100 text-slate-500" };
  if (!p.hasMeta)
    return { label: "بدون متا", className: "bg-red-50 text-red-500" };
  const goodTitle = p.titleLength >= 30 && p.titleLength <= 60;
  const goodDesc = p.descriptionLength >= 70 && p.descriptionLength <= 160;
  if (goodTitle && goodDesc && p.focusKeyword)
    return { label: "عالی", className: "bg-emerald-50 text-emerald-600" };
  return { label: "نیازمند بهبود", className: "bg-amber-50 text-amber-600" };
}

export default function SeoPages() {
  const [pages, setPages] = useState<PageRow[]>([]);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<{ pages: PageRow[] }>("/api/admin/seo/pages").then((res) => {
      if (res.ok && res.data) setPages(res.data.pages);
      setLoading(false);
    });
  }, []);

  const visible = pages.filter(
    (p) =>
      (!filter || p.pageType === filter) &&
      (!search.trim() || p.title.includes(search.trim()) || p.path.includes(search.trim()))
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          📝 متای صفحات{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(pages.length)})
          </span>
        </h1>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="جستجوی صفحه..."
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400 sm:w-56"
        />
      </div>

      <div className="flex gap-1.5">
        {[
          { key: "", label: "همه" },
          { key: "static", label: "صفحات ثابت" },
          { key: "category", label: "دسته‌بندی‌ها" },
          { key: "product", label: "محصولات" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={`rounded-lg px-3.5 py-1.5 text-xs transition ${
              filter === t.key
                ? "bg-slate-800 font-medium text-white"
                : "bg-white text-slate-500 ring-1 ring-slate-200 hover:text-slate-800"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">صفحه</th>
              <th className="px-3 py-3 font-medium">نوع</th>
              <th className="px-3 py-3 font-medium">عنوان متا</th>
              <th className="px-3 py-3 font-medium">توضیحات</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-5 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={6} text="در حال بارگذاری..." />
            ) : visible.length === 0 ? (
              <EmptyRow colSpan={6} text="صفحه‌ای یافت نشد" />
            ) : (
              visible.map((p) => {
                const status = statusOf(p);
                return (
                  <tr
                    key={`${p.pageType}-${p.objectKey}`}
                    className="hover:bg-slate-50/60"
                  >
                    <td className="px-5 py-3">
                      <p className="max-w-[240px] truncate text-xs text-slate-700">
                        {p.title}
                      </p>
                      <code
                        dir="ltr"
                        className="text-[10px] text-slate-400"
                      >
                        {p.path}
                      </code>
                    </td>
                    <td className="px-3 py-3 text-[11px] text-slate-500">
                      {TYPE_FA[p.pageType]}
                    </td>
                    <td className="px-3 py-3">
                      <LengthBadge len={p.titleLength} min={30} max={60} />
                    </td>
                    <td className="px-3 py-3">
                      <LengthBadge len={p.descriptionLength} min={70} max={160} />
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`rounded-lg px-2.5 py-1 text-[11px] font-medium ${status.className}`}
                      >
                        {status.label}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <Link
                        href={`/admin/seo/editor?type=${p.pageType}&key=${encodeURIComponent(p.objectKey)}`}
                        className="text-xs text-brand-600 hover:underline"
                      >
                        ویرایش سئو
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LengthBadge({
  len,
  min,
  max,
}: {
  len: number;
  min: number;
  max: number;
}) {
  if (len === 0)
    return <span className="text-[11px] text-slate-300">تنظیم نشده</span>;
  const good = len >= min && len <= max;
  return (
    <span
      className={`text-[11px] font-num ${
        good ? "text-emerald-600" : "text-amber-600"
      }`}
    >
      {faNum(len)} حرف
    </span>
  );
}
