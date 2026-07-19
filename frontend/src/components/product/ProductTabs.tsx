"use client";

import { useState } from "react";
import type { Product } from "@/lib/products";

const tabs = [
  { key: "specs", label: "مشخصات" },
  { key: "intro", label: "معرفی" },
  { key: "reviews", label: "دیدگاه‌ها" },
] as const;

type TabKey = (typeof tabs)[number]["key"];

export default function ProductTabs({ product }: { product: Product }) {
  const [active, setActive] = useState<TabKey>("specs");

  return (
    <div className="rounded-2xl border border-slate-100 bg-white">
      {/* سر تب‌ها */}
      <div className="flex gap-1 border-b border-slate-100 px-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActive(t.key)}
            className={`relative px-4 py-3 text-sm font-medium transition ${
              active === t.key
                ? "text-brand-700"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
            {active === t.key && (
              <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-brand-600" />
            )}
          </button>
        ))}
      </div>

      <div className="p-5">
        {active === "specs" && (
          <table className="w-full text-sm">
            <tbody className="divide-y divide-slate-100">
              {product.specs?.map((s) => (
                <tr key={s.label}>
                  <td className="w-40 py-3 align-top text-slate-400">
                    {s.label}
                  </td>
                  <td className="py-3 text-slate-700">{s.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {active === "intro" && (
          <p className="text-sm leading-8 text-slate-600">
            {product.description}
          </p>
        )}

        {active === "reviews" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl bg-slate-50 p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-slate-800 font-num">
                  {product.rating.toLocaleString("fa-IR")}
                </div>
                <div className="text-amber-400">★★★★★</div>
                <div className="mt-1 text-xs text-slate-400 font-num">
                  از {product.ratingCount.toLocaleString("fa-IR")} دیدگاه
                </div>
              </div>
              <p className="flex-1 text-sm leading-7 text-slate-500">
                خریداران از کیفیت و عملکرد این محصول رضایت بالایی داشته‌اند. شما
                هم می‌توانید پس از خرید، دیدگاه خود را ثبت کنید.
              </p>
            </div>

            {/* نمونه دیدگاه */}
            <div className="rounded-xl border border-slate-100 p-4">
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">
                  کاربر دیجی‌سبز
                </span>
                <span className="text-amber-400 text-xs">★★★★★</span>
              </div>
              <p className="text-sm leading-7 text-slate-500">
                کیفیت ساخت عالی بود و خیلی سریع به دستم رسید. کاملاً راضی هستم و
                پیشنهاد می‌کنم.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
