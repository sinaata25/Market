"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import {
  categories as categoryFallback,
  type Category,
} from "@/lib/products";

type CategoryLink = { slug: string; title: string };

type SectionItem = {
  category: CategoryLink;
  depth: number;
  pathKey: string;
};

type CategorySection = {
  heading: CategoryLink;
  items: SectionItem[];
  pathKey: string;
};

function collectSectionItems(
  category: Category,
  categoryBySlug: Map<string, Category>,
  path: Set<string>,
  depth: number,
  items: SectionItem[]
) {
  for (const child of category.sub) {
    if (path.has(child.slug)) continue;
    const childPath = new Set([...path, child.slug]);
    items.push({
      category: child,
      depth,
      pathKey: [...childPath].join(">"),
    });
    const fullChild = categoryBySlug.get(child.slug);
    if (fullChild) {
      collectSectionItems(
        fullChild,
        categoryBySlug,
        childPath,
        depth + 1,
        items
      );
    }
  }
}

export default function CategoryMenu() {
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [categories, setCategories] = useState<Category[]>(categoryFallback);
  const rootCategories = categories.filter(
    (category) => category.isTopLevel !== false
  );
  const active = rootCategories[activeIndex];
  const categoryBySlug = new Map(
    categories.map((category) => [category.slug, category])
  );
  const sections: CategorySection[] = (active?.sub ?? []).map((child) => {
    const items: SectionItem[] = [];
    const fullChild = categoryBySlug.get(child.slug);
    const path = new Set([active.slug, child.slug]);
    if (fullChild) {
      collectSectionItems(fullChild, categoryBySlug, path, 0, items);
    }
    return {
      heading: child,
      items,
      pathKey: [...path].join(">"),
    };
  });

  useEffect(() => {
    let ignore = false;
    api.get<{ categories: Category[] }>("/api/categories").then((res) => {
      if (!ignore && res.ok && res.data) {
        setCategories(res.data.categories);
        const firstPopulatedRoot = res.data.categories
          .filter((category) => category.isTopLevel !== false)
          .findIndex((category) => category.sub.length > 0);
        setActiveIndex(firstPopulatedRoot >= 0 ? firstPopulatedRoot : 0);
      }
    });
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={menuRef} className="relative">
      {/* دکمه دسته‌بندی محصولات */}
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="product-category-menu"
        aria-haspopup="menu"
        className={`flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition ${
          open
            ? "bg-brand-50 text-brand-700"
            : "text-slate-700 hover:bg-slate-50"
        }`}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          className="h-5 w-5"
        >
          <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
        </svg>
        <span>دسته‌بندی محصولات</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.17l3.71-3.94a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* پنل کشویی (مگامنو) */}
      {open && active && (
        <div
          id="product-category-menu"
          className="fixed inset-x-2 top-[10.75rem] z-50 pt-2 lg:absolute lg:inset-x-auto lg:right-0 lg:top-full"
        >
          <div className="flex h-[min(36rem,calc(100dvh-11.25rem))] min-h-0 w-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_22px_60px_-18px_rgba(15,23,42,0.35)] lg:h-[min(580px,calc(100dvh-9rem))] lg:w-[min(1120px,calc(100vw-2rem))] lg:flex-row lg:rounded-b-2xl lg:rounded-tl-2xl lg:rounded-tr-none">
            {/* ستون دسته‌های اصلی */}
            <ul
              aria-label="دسته‌بندی‌های اصلی"
              className="flex w-full shrink-0 overflow-x-auto border-b border-slate-200 bg-slate-50/80 p-2 lg:block lg:w-60 lg:overflow-y-auto lg:border-b-0 lg:border-l lg:py-2"
            >
              {rootCategories.map((c, i) => (
                <li key={c.slug} className="shrink-0">
                  <Link
                    href={`/category/${c.slug}`}
                    onMouseEnter={() => setActiveIndex(i)}
                    onFocus={() => setActiveIndex(i)}
                    onClick={() => setOpen(false)}
                    className={`flex min-h-11 min-w-36 items-center gap-2 rounded-xl border-b-2 px-3 py-2.5 text-xs transition lg:min-h-12 lg:min-w-0 lg:gap-3 lg:rounded-none lg:border-r-2 lg:border-b-0 lg:px-4 lg:py-3 ${
                      activeIndex === i
                        ? "border-brand-600 bg-white font-bold text-brand-700"
                        : "border-transparent text-slate-600 hover:bg-white hover:text-brand-700"
                    }`}
                  >
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-slate-400 shadow-sm ring-1 ring-slate-100">
                      {c.icon ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={c.icon}
                          alt=""
                          className="h-4 w-4 object-contain"
                        />
                      ) : (
                        <svg
                          aria-hidden="true"
                          viewBox="0 0 20 20"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          className="h-4 w-4"
                        >
                          <rect x="3" y="3" width="5" height="5" rx="1" />
                          <rect x="12" y="3" width="5" height="5" rx="1" />
                          <rect x="3" y="12" width="5" height="5" rx="1" />
                          <rect x="12" y="12" width="5" height="5" rx="1" />
                        </svg>
                      )}
                    </span>
                    <span className="min-w-0 flex-1 truncate">{c.title}</span>
                    <span
                      aria-hidden="true"
                      className={`text-base ${
                        activeIndex === i
                          ? "text-brand-500"
                          : "text-slate-300"
                      }`}
                    >
                      ‹
                    </span>
                  </Link>
                </li>
              ))}
            </ul>

            {/* ستون زیردسته‌ها */}
            <div className="min-w-0 flex-1 overflow-y-auto bg-white">
              <div className="sticky top-0 z-10 border-b border-slate-100 bg-white/95 px-4 py-3 backdrop-blur sm:px-6 sm:py-4">
                <Link
                  href={`/category/${active.slug}`}
                  onClick={() => setOpen(false)}
                  className="inline-flex items-center gap-2 text-xs font-bold text-brand-700 transition hover:text-brand-800"
                >
                  همه محصولات {active.title}
                  <span aria-hidden="true" className="text-base">
                    ‹
                  </span>
                </Link>
              </div>

              <div className="p-4 sm:p-6">
                {sections.length > 0 ? (
                  <div className="grid grid-cols-1 items-start gap-x-6 gap-y-6 sm:grid-cols-2 lg:grid-cols-3 lg:gap-x-10 lg:gap-y-7">
                    {sections.map((section) => (
                      <section key={section.pathKey} className="min-w-0">
                        <Link
                          href={`/category/${section.heading.slug}`}
                          onClick={() => setOpen(false)}
                          className="group mb-2.5 flex items-center gap-2 text-sm font-bold text-slate-800 transition hover:text-brand-700"
                        >
                          <span className="h-4 w-0.5 rounded-full bg-brand-600" />
                          <span className="truncate">{section.heading.title}</span>
                          <span
                            aria-hidden="true"
                            className="text-base text-slate-300 transition group-hover:text-brand-500"
                          >
                            ‹
                          </span>
                        </Link>

                        {section.items.length > 0 && (
                          <ul className="space-y-2 border-r border-slate-100 pr-3">
                            {section.items.map(
                              ({ category, depth, pathKey }) => (
                                <li key={pathKey}>
                                  <Link
                                    href={`/category/${category.slug}`}
                                    onClick={() => setOpen(false)}
                                    className={`block truncate text-xs leading-6 transition hover:text-brand-700 ${
                                      depth > 0
                                        ? "text-slate-400"
                                        : "text-slate-500"
                                    }`}
                                    style={{ paddingRight: `${depth * 10}px` }}
                                  >
                                    {category.title}
                                  </Link>
                                </li>
                              )
                            )}
                          </ul>
                        )}
                      </section>
                    ))}
                  </div>
                ) : (
                  <div className="grid min-h-56 place-items-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-6 text-center">
                    <div>
                      <span className="mb-3 block text-3xl">🗂️</span>
                      <p className="text-sm font-medium text-slate-600">
                        زیردسته‌ای برای {active.title} تعریف نشده است
                      </p>
                      <Link
                        href={`/category/${active.slug}`}
                        onClick={() => setOpen(false)}
                        className="mt-3 inline-block text-xs font-bold text-brand-700 hover:text-brand-800"
                      >
                        مشاهده محصولات این دسته
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
