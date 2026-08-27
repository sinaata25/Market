"use client";

import { useMemo, useState } from "react";
import type {
  ManagedStaticPage,
  SupportPageContent,
} from "@/lib/static-page-types";
import { normalizeSearchText, searchTextIncludes } from "@/lib/search";

const supportGroupRoutes = [
  { slug: "order", emoji: "🛒", sectionId: "faq-order" },
  { slug: "payment", emoji: "💳", sectionId: "faq-payment" },
  { slug: "shipping", emoji: "🚚", sectionId: "faq-shipping" },
  { slug: "return", emoji: "↩️", sectionId: "faq-return" },
  { slug: "warranty", emoji: "✅", sectionId: "faq-warranty" },
  { slug: "account", emoji: "👤", sectionId: "faq-account" },
] as const;

type SupportContentProps = {
  content: SupportPageContent;
  sections: ManagedStaticPage<"support">["sections"];
  contactPhone: string;
};

export default function SupportContent({
  content,
  sections,
  contactPhone,
}: SupportContentProps) {
  const [query, setQuery] = useState("");
  const [activeGroup, setActiveGroup] = useState(
    supportGroupRoutes.find((route) => sections[route.sectionId])?.slug ?? ""
  );
  const [openKey, setOpenKey] = useState<string | null>(null);

  const groups = useMemo(
    () =>
      supportGroupRoutes.map((route, index) => ({
        ...route,
        ...content.groups[index],
      })).filter((group) => sections[group.sectionId]),
    [content.groups, sections]
  );
  const normalizedQuery = normalizeSearchText(query);
  const isSearching = normalizedQuery.length > 0;

  const visibleGroups = useMemo(() => {
    if (!isSearching) {
      return groups.filter((group) => group.slug === activeGroup);
    }
    return groups
      .map((group) => ({
        ...group,
        items: group.items.filter(
          (item) =>
            searchTextIncludes(item.question, normalizedQuery) ||
            searchTextIncludes(item.answer, normalizedQuery)
        ),
      }))
      .filter((group) => group.items.length > 0);
  }, [activeGroup, groups, isSearching, normalizedQuery]);

  return (
    <div className="site-shell py-8">
      {sections.hero && <section className="mb-8 rounded-3xl bg-gradient-to-l from-brand-700 to-brand-500 px-6 py-10 text-center text-white sm:px-12">
        <h1 className="mb-2 text-2xl font-bold">{content.hero.title}</h1>
        <p className="mb-6 text-sm text-brand-50">{content.hero.description}</p>
        <div className="relative mx-auto max-w-xl">
          <input
            type="search"
            maxLength={200}
            aria-label="جستجو در پرسش‌های متداول"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setOpenKey(null);
            }}
            placeholder={content.hero.searchPlaceholder}
            className="w-full rounded-2xl border border-transparent bg-white px-12 py-3.5 text-sm text-slate-700 outline-none focus:border-brand-300"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">
            🔍
          </span>
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setOpenKey(null);
              }}
              aria-label="پاک کردن جستجو"
              className="absolute left-3 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-100"
            >
              ×
            </button>
          )}
        </div>
      </section>}

      <div className="flex flex-col gap-6 lg:flex-row">
        {!isSearching && groups.length > 0 && (
          <aside className="lg:w-64 lg:shrink-0">
            <div className="rounded-2xl border border-slate-100 bg-white p-2">
              <h2 className="px-3 py-2 text-xs font-bold text-slate-400">
                {content.sidebarTitle}
              </h2>
              <ul className="space-y-1">
                {groups.map((group) => (
                  <li key={group.slug}>
                    <button
                      onClick={() => {
                        setActiveGroup(group.slug);
                        setOpenKey(null);
                      }}
                      className={`flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-right text-sm transition ${
                        activeGroup === group.slug
                          ? "bg-brand-50 font-medium text-brand-700"
                          : "text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <span className="text-base">{group.emoji}</span>
                      <span className="flex-1">{group.title}</span>
                      <span className="text-xs text-slate-300">‹</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        )}

        <div className="flex-1 space-y-6">
          {isSearching && visibleGroups.length === 0 && (
            <div className="rounded-2xl border border-slate-100 bg-white p-10 text-center text-sm text-slate-500">
              {content.noResults.beforeQuery}{query}{content.noResults.afterQuery}
            </div>
          )}

          {visibleGroups.map((group) => (
            <section key={group.slug}>
              <h2 className="mb-3 flex items-center gap-2 text-base font-bold text-slate-800">
                <span className="text-lg">{group.emoji}</span>
                {group.title}
              </h2>
              <div className="divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-100 bg-white">
                {group.items.map((item, index) => {
                  const key = `${group.slug}-${index}`;
                  const open = openKey === key;
                  return (
                    <div key={key}>
                      <button
                        onClick={() => setOpenKey(open ? null : key)}
                        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-right text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                      >
                        <span>{item.question}</span>
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
                            {item.answer}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}

          {sections.contact && <div className="rounded-2xl border border-brand-100 bg-brand-50 p-6 text-center">
            <p className="mb-1 font-bold text-slate-800">
              {content.contact.title}
            </p>
            <p className="mb-4 text-sm text-slate-500">
              {content.contact.description}
            </p>
            <div className="flex flex-wrap justify-center gap-3 text-sm">
              <a
                href={`tel:${contactPhone}`}
                className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white transition hover:bg-brand-700"
              >
                <span aria-hidden="true">📞</span>{" "}
                {content.contact.phoneLabel}
              </a>
              <a
                href={content.contact.onlineUrl}
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-medium text-slate-600 transition hover:border-brand-300"
              >
                <span aria-hidden="true">💬</span>{" "}
                {content.contact.onlineLabel}
              </a>
            </div>
          </div>}
        </div>
      </div>
    </div>
  );
}
