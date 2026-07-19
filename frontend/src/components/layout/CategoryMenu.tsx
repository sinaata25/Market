"use client";

import { useState } from "react";
import Link from "next/link";
import { categories } from "@/lib/products";

export default function CategoryMenu() {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const active = categories[activeIndex];

  return (
    <div
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      {/* دکمه دسته‌بندی محصولات */}
      <button
        className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
          open ? "text-brand-700" : "text-slate-700"
        }`}
      >
        <span>☰</span>
        <span>دسته‌بندی محصولات</span>
        <span
          className={`text-xs transition-transform ${open ? "rotate-180" : ""}`}
        >
          ▾
        </span>
      </button>

      {/* پنل کشویی (مگامنو) */}
      {open && (
        <div className="absolute right-0 top-full z-50 pt-2">
          <div className="flex w-[640px] overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-xl">
            {/* ستون دسته‌های اصلی */}
            <ul className="w-56 shrink-0 border-l border-slate-100 bg-slate-50 py-2">
              {categories.map((c, i) => (
                <li key={c.slug}>
                  <Link
                    href={`/category/${c.slug}`}
                    onMouseEnter={() => setActiveIndex(i)}
                    className={`flex items-center justify-between gap-2 px-4 py-2.5 text-sm transition ${
                      activeIndex === i
                        ? "bg-white font-medium text-brand-700"
                        : "text-slate-600 hover:text-brand-700"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-base">{c.emoji}</span>
                      {c.title}
                    </span>
                    <span className="text-xs text-slate-300">‹</span>
                  </Link>
                </li>
              ))}
            </ul>

            {/* ستون زیردسته‌ها */}
            <div className="flex-1 p-5">
              <Link
                href={`/category/${active.slug}`}
                className="mb-4 inline-flex items-center gap-2 text-sm font-bold text-slate-800 hover:text-brand-700"
              >
                <span className="text-lg">{active.emoji}</span>
                {active.title}
                <span className="text-xs text-brand-600">(مشاهده همه)</span>
              </Link>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-3">
                {active.sub.map((s) => (
                  <li key={s}>
                    <Link
                      href={`/category/${active.slug}`}
                      className="text-sm text-slate-500 transition hover:text-brand-700"
                    >
                      {s}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
