"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { faNum, EmptyRow } from "@/components/admin/ui";

type Img = {
  id: number;
  url: string;
  alt: string;
  productId: number;
  productTitle: string;
};

export default function SeoImages() {
  const [images, setImages] = useState<Img[]>([]);
  const [edited, setEdited] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get<{ images: Img[] }>("/api/admin/seo/images").then((res) => {
      if (res.ok && res.data) setImages(res.data.images);
      setLoading(false);
    });
  }, []);

  const dirtyCount = Object.keys(edited).length;
  const missingCount = images.filter(
    (i) => !(edited[i.id] ?? i.alt).trim()
  ).length;

  function setAlt(id: number, value: string) {
    setEdited((prev) => ({ ...prev, [id]: value }));
  }

  // پرکردن خودکار Altهای خالی با عنوان محصول
  function fillMissing() {
    const patch: Record<number, string> = { ...edited };
    for (const img of images) {
      if (!(patch[img.id] ?? img.alt).trim()) {
        patch[img.id] = img.productTitle;
      }
    }
    setEdited(patch);
  }

  async function saveAll() {
    if (dirtyCount === 0) return;
    setSaving(true);
    setMessage("");
    const items = Object.entries(edited).map(([id, alt]) => ({
      id: Number(id),
      alt,
    }));
    const res = await api.patch<{ updated: number }>(
      "/api/admin/seo/images",
      { items }
    );
    setSaving(false);
    if (res.ok && res.data) {
      setImages((prev) =>
        prev.map((img) =>
          edited[img.id] !== undefined
            ? { ...img, alt: edited[img.id] }
            : img
        )
      );
      setEdited({});
      setMessage(`✅ ${res.data.updated.toLocaleString("fa-IR")} تصویر ذخیره شد`);
    } else {
      setMessage(res.error ?? "خطا در ذخیره");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          🖼️ Alt تصاویر{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(images.length)} تصویر — {faNum(missingCount)} بدون Alt)
          </span>
        </h1>
        <div className="flex gap-2">
          <button
            onClick={fillMissing}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs text-slate-600 transition hover:border-brand-400"
          >
            ✨ پر کردن خودکار خالی‌ها
          </button>
          <button
            onClick={saveAll}
            disabled={saving || dirtyCount === 0}
            className="rounded-xl bg-brand-600 px-5 py-2 text-xs font-bold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {saving
              ? "در حال ذخیره..."
              : `ذخیره گروهی${dirtyCount ? ` (${faNum(dirtyCount)})` : ""}`}
          </button>
        </div>
      </div>

      {message && (
        <p className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white">
          {message}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">تصویر</th>
              <th className="px-3 py-3 font-medium">محصول</th>
              <th className="px-5 py-3 font-medium">متن جایگزین (Alt)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={3} text="در حال بارگذاری..." />
            ) : images.length === 0 ? (
              <EmptyRow colSpan={3} text="تصویری وجود ندارد" />
            ) : (
              images.map((img) => {
                const value = edited[img.id] ?? img.alt;
                return (
                  <tr key={img.id} className="hover:bg-slate-50/60">
                    <td className="px-5 py-3">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={img.url}
                        alt={value}
                        className="h-14 w-14 rounded-lg object-cover"
                      />
                    </td>
                    <td className="max-w-[200px] truncate px-3 py-3 text-xs text-slate-600">
                      {img.productTitle}
                    </td>
                    <td className="px-5 py-3">
                      <input
                        value={value}
                        onChange={(e) => setAlt(img.id, e.target.value)}
                        placeholder="توضیح تصویر برای موتور جستجو..."
                        className={`w-full rounded-xl border px-3 py-2 text-xs outline-none transition focus:bg-white ${
                          !value.trim()
                            ? "border-red-200 bg-red-50/50 focus:border-red-400"
                            : edited[img.id] !== undefined
                              ? "border-amber-300 bg-amber-50/50 focus:border-amber-400"
                              : "border-slate-200 bg-slate-50 focus:border-brand-400"
                        }`}
                      />
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
