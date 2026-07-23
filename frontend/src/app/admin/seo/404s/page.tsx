"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import { faNum, faDateTime, EmptyRow } from "@/components/admin/ui";

type Log = {
  id: number;
  path: string;
  hits: number;
  referer: string;
  lastSeen: string;
};

export default function Seo404s() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    api.get<{ logs: Log[] }>("/api/admin/seo/404s").then((res) => {
      if (res.ok && res.data) setLogs(res.data.logs);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function clearAll() {
    if (!confirm("همه‌ی گزارش‌های ۴۰۴ پاک شوند؟")) return;
    await api.delete("/api/admin/seo/404s");
    load();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-800">
          🚫 خطاهای ۴۰۴{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(logs.length)})
          </span>
        </h1>
        {logs.length > 0 && (
          <button
            onClick={clearAll}
            className="rounded-xl border border-red-100 bg-red-50 px-4 py-2 text-xs text-red-500 transition hover:bg-red-100"
          >
            پاک‌کردن همه
          </button>
        )}
      </div>

      <p className="rounded-xl bg-blue-50 px-4 py-3 text-xs leading-6 text-blue-600">
        💡 برای هر مسیر ۴۰۴ می‌توانید در بخش «ریدایرکت‌ها» یک ریدایرکت ۳۰۱ به
        صفحه‌ی مناسب ثبت کنید.
      </p>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">مسیر</th>
              <th className="px-3 py-3 font-medium">دفعات</th>
              <th className="px-3 py-3 font-medium">ارجاع‌دهنده</th>
              <th className="px-3 py-3 font-medium">آخرین بازدید</th>
              <th className="px-5 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={5} text="در حال بارگذاری..." />
            ) : logs.length === 0 ? (
              <EmptyRow
                colSpan={5}
                text="خطای ۴۰۴ ثبت نشده است — عالی! 🎉"
              />
            ) : (
              logs.map((l) => (
                <tr key={l.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3">
                    <code dir="ltr" className="text-xs text-slate-600">
                      {l.path}
                    </code>
                  </td>
                  <td className="px-3 py-3">
                    <span className="rounded-md bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-500 font-num">
                      {faNum(l.hits)}
                    </span>
                  </td>
                  <td className="max-w-[180px] truncate px-3 py-3 text-[11px] text-slate-400">
                    {l.referer || "—"}
                  </td>
                  <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
                    {faDateTime(l.lastSeen)}
                  </td>
                  <td className="px-5 py-3">
                    <Link
                      href="/admin/seo/redirects"
                      className="text-xs text-brand-600 hover:underline"
                    >
                      ثبت ریدایرکت
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
