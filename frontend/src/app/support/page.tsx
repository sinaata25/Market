"use client";

import { useMemo, useState } from "react";
import { faqGroups } from "@/lib/faq";

export default function SupportPage() {
  const [query, setQuery] = useState("");
  const [activeGroup, setActiveGroup] = useState(faqGroups[0].slug);
  const [openKey, setOpenKey] = useState<string | null>(null);

  const isSearching = query.trim().length > 0;

  // نتایج بر اساس جستجو یا دسته فعال
  const visibleGroups = useMemo(() => {
    if (!isSearching) {
      return faqGroups.filter((g) => g.slug === activeGroup);
    }
    const q = query.trim();
    return faqGroups
      .map((g) => ({
        ...g,
        items: g.items.filter(
          (it) => it.q.includes(q) || it.a.includes(q)
        ),
      }))
      .filter((g) => g.items.length > 0);
  }, [query, activeGroup, isSearching]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* سربرگ + جستجو */}
      <section className="mb-8 rounded-3xl bg-gradient-to-l from-brand-700 to-brand-500 px-6 py-10 text-center text-white sm:px-12">
        <h1 className="mb-2 text-2xl font-bold">سوالی دارید؟</h1>
        <p className="mb-6 text-sm text-brand-50">
          پاسخ پرسش‌های پرتکرار درباره خرید، پرداخت، ارسال و پشتیبانی را اینجا
          پیدا کنید.
        </p>
        <div className="relative mx-auto max-w-xl">
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpenKey(null);
            }}
            placeholder="جستجوی سوال... (مثلاً ارسال، بازگشت کالا)"
            className="w-full rounded-2xl border border-transparent bg-white px-5 py-3.5 pr-12 text-sm text-slate-700 outline-none focus:border-brand-300"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
            🔍
          </span>
        </div>
      </section>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* سایدبار دسته‌بندی‌ها */}
        {!isSearching && (
          <aside className="lg:w-64 lg:shrink-0">
            <div className="rounded-2xl border border-slate-100 bg-white p-2">
              <h2 className="px-3 py-2 text-xs font-bold text-slate-400">
                دسته‌بندی موضوعات
              </h2>
              <ul className="space-y-1">
                {faqGroups.map((g) => (
                  <li key={g.slug}>
                    <button
                      onClick={() => {
                        setActiveGroup(g.slug);
                        setOpenKey(null);
                      }}
                      className={`flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-right text-sm transition ${
                        activeGroup === g.slug
                          ? "bg-brand-50 font-medium text-brand-700"
                          : "text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <span className="text-base">{g.emoji}</span>
                      <span className="flex-1">{g.title}</span>
                      <span className="text-xs text-slate-300">‹</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        )}

        {/* محتوای سوال و جواب */}
        <div className="flex-1 space-y-6">
          {visibleGroups.length === 0 && (
            <div className="rounded-2xl border border-slate-100 bg-white p-10 text-center text-sm text-slate-500">
              نتیجه‌ای برای «{query}» یافت نشد. عبارت دیگری را امتحان کنید.
            </div>
          )}

          {visibleGroups.map((g) => (
            <section key={g.slug}>
              <h2 className="mb-3 flex items-center gap-2 text-base font-bold text-slate-800">
                <span className="text-lg">{g.emoji}</span>
                {g.title}
              </h2>
              <div className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-100 bg-white">
                {g.items.map((it, i) => {
                  const key = `${g.slug}-${i}`;
                  const open = openKey === key;
                  return (
                    <div key={key}>
                      <button
                        onClick={() => setOpenKey(open ? null : key)}
                        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-right text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                      >
                        <span>{it.q}</span>
                        <span
                          className={`shrink-0 text-brand-600 transition-transform ${
                            open ? "rotate-180" : ""
                          }`}
                        >
                          ▾
                        </span>
                      </button>
                      <div
                        className={`grid transition-all duration-300 ${
                          open
                            ? "grid-rows-[1fr] opacity-100"
                            : "grid-rows-[0fr] opacity-0"
                        }`}
                      >
                        <div className="overflow-hidden">
                          <p className="px-5 pb-4 text-sm leading-7 text-slate-500">
                            {it.a}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}

          {/* تماس با پشتیبانی */}
          <div className="rounded-2xl border border-brand-100 bg-brand-50 p-6 text-center">
            <p className="mb-1 font-bold text-slate-800">
              پاسخ سوال خود را پیدا نکردید؟
            </p>
            <p className="mb-4 text-sm text-slate-500">
              کارشناسان ما ۷ روز هفته آماده پاسخگویی به شما هستند.
            </p>
            <div className="flex flex-wrap justify-center gap-3 text-sm">
              <a
                href="tel:02100000000"
                className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white transition hover:bg-brand-700"
              >
                📞 تماس با پشتیبانی
              </a>
              <a
                href="#"
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-medium text-slate-600 transition hover:border-brand-300"
              >
                💬 گفتگوی آنلاین
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
