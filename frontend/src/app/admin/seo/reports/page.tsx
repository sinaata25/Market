"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { faNum, faDateTime, EmptyRow } from "@/components/admin/ui";

type Result = {
  url: string;
  kind: string;
  statusCode: number | null;
  responseMs: number | null;
  ok: boolean;
  checkedAt: string;
};

function speedLabel(ms: number | null) {
  if (ms === null) return { label: "—", cls: "text-slate-400" };
  if (ms < 300) return { label: "سریع", cls: "text-emerald-600" };
  if (ms < 1000) return { label: "متوسط", cls: "text-amber-600" };
  return { label: "کند", cls: "text-red-500" };
}

export default function SeoReports() {
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [filter, setFilter] = useState("");

  const load = useCallback(() => {
    api.get<{ results: Result[] }>("/api/admin/seo/scan").then((res) => {
      if (res.ok && res.data) setResults(res.data.results);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runScan() {
    setScanning(true);
    const res = await api.post<{ checked: number }>("/api/admin/seo/scan");
    setScanning(false);
    if (res.ok) load();
  }

  const broken = results.filter((r) => !r.ok);
  const visible = results.filter((r) => {
    if (filter === "broken") return !r.ok;
    if (filter === "page") return r.kind === "page";
    if (filter === "link") return r.kind === "link";
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          ⚡ سرعت صفحات و لینک‌های شکسته
        </h1>
        <button
          onClick={runScan}
          disabled={scanning}
          className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {scanning ? "در حال اسکن... (چند لحظه)" : "🔍 اجرای اسکن جدید"}
        </button>
      </div>

      {results.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-2xl border border-slate-100 bg-white p-4 text-center">
            <p className="text-xl font-bold text-slate-800 font-num">
              {faNum(results.length)}
            </p>
            <p className="text-[11px] text-slate-400">آدرس بررسی‌شده</p>
          </div>
          <div className="rounded-2xl border border-slate-100 bg-white p-4 text-center">
            <p
              className={`text-xl font-bold font-num ${
                broken.length ? "text-red-500" : "text-emerald-600"
              }`}
            >
              {faNum(broken.length)}
            </p>
            <p className="text-[11px] text-slate-400">لینک شکسته</p>
          </div>
          <div className="rounded-2xl border border-slate-100 bg-white p-4 text-center">
            <p className="text-xl font-bold text-slate-800 font-num">
              {faNum(
                Math.round(
                  results
                    .filter((r) => r.responseMs !== null)
                    .reduce((s, r) => s + (r.responseMs ?? 0), 0) /
                    Math.max(
                      results.filter((r) => r.responseMs !== null).length,
                      1
                    )
                )
              )}
              <span className="text-xs"> ms</span>
            </p>
            <p className="text-[11px] text-slate-400">میانگین زمان پاسخ</p>
          </div>
        </div>
      )}

      <div className="flex gap-1.5">
        {[
          { key: "", label: "همه" },
          { key: "page", label: "صفحات" },
          { key: "link", label: "تصاویر/لینک‌ها" },
          { key: "broken", label: "فقط خراب‌ها" },
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
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">آدرس</th>
              <th className="px-3 py-3 font-medium">نوع</th>
              <th className="px-3 py-3 font-medium">کد وضعیت</th>
              <th className="px-3 py-3 font-medium">زمان پاسخ</th>
              <th className="px-5 py-3 font-medium">زمان بررسی</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={5} text="در حال بارگذاری..." />
            ) : visible.length === 0 ? (
              <EmptyRow
                colSpan={5}
                text={
                  results.length === 0
                    ? "هنوز اسکنی اجرا نشده — دکمه «اجرای اسکن جدید» را بزنید"
                    : "موردی یافت نشد"
                }
              />
            ) : (
              visible.map((r, i) => {
                const speed = speedLabel(r.responseMs);
                return (
                  <tr key={i} className="hover:bg-slate-50/60">
                    <td className="max-w-[280px] truncate px-5 py-3">
                      <code dir="ltr" className="text-xs text-slate-600">
                        {r.url.replace("http://localhost:3000", "")}
                      </code>
                    </td>
                    <td className="px-3 py-3 text-[11px] text-slate-500">
                      {r.kind === "page" ? "صفحه" : "تصویر"}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`rounded-md px-2 py-0.5 text-[11px] font-bold font-num ${
                          r.ok
                            ? "bg-emerald-50 text-emerald-600"
                            : "bg-red-50 text-red-500"
                        }`}
                      >
                        {r.statusCode ?? "خطا"}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-xs">
                      <span className={`font-num ${speed.cls}`}>
                        {r.responseMs !== null
                          ? `${faNum(r.responseMs)} ms — ${speed.label}`
                          : "—"}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-[11px] text-slate-400 font-num">
                      {faDateTime(r.checkedAt)}
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
