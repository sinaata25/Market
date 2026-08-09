"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/client-api";
import {
  categories as categoryFallback,
  type Category,
} from "@/lib/products";

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
  const descendants: {
    category: { slug: string; title: string };
    depth: number;
    pathKey: string;
  }[] = [];

  function collectDescendants(
    category: Category,
    depth: number,
    path: Set<string>
  ) {
    for (const child of category.sub) {
      if (path.has(child.slug)) continue;
      const childPath = new Set([...path, child.slug]);
      descendants.push({
        category: child,
        depth,
        pathKey: [...childPath].join(">"),
      });
      const fullChild = categoryBySlug.get(child.slug);
      if (fullChild) {
        collectDescendants(fullChild, depth + 1, childPath);
      }
    }
  }

  if (active) collectDescendants(active, 0, new Set([active.slug]));

  useEffect(() => {
    let ignore = false;
    api.get<{ categories: Category[] }>("/api/categories").then((res) => {
      if (!ignore && res.ok && res.data) {
        setCategories(res.data.categories);
        setActiveIndex(0);
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
      {open && active && (
        <div
          id="product-category-menu"
          className="absolute right-0 top-full z-50 pt-2"
        >
          <div className="flex w-[640px] overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-xl">
            {/* ستون دسته‌های اصلی */}
            <ul className="w-56 shrink-0 border-l border-slate-100 bg-slate-50 py-2">
              {rootCategories.map((c, i) => (
                <li key={c.slug}>
                  <Link
                    href={`/category/${c.slug}`}
                    onMouseEnter={() => setActiveIndex(i)}
                    onClick={() => setOpen(false)}
                    className={`flex items-center justify-between gap-2 px-4 py-2.5 text-sm transition ${
                      activeIndex === i
                        ? "bg-white font-medium text-brand-700"
                        : "text-slate-600 hover:text-brand-700"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      {c.icon && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={c.icon}
                          alt=""
                          className="h-4 w-4 shrink-0 object-contain"
                        />
                      )}
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
                onClick={() => setOpen(false)}
                className="mb-4 inline-flex items-center gap-2 text-sm font-bold text-slate-800 hover:text-brand-700"
              >
                {active.icon && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={active.icon}
                    alt=""
                    className="h-5 w-5 shrink-0 object-contain"
                  />
                )}
                {active.title}
                <span className="text-xs text-brand-600">(مشاهده همه)</span>
              </Link>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-3">
                {descendants.map(({ category, depth, pathKey }) => (
                  <li key={pathKey}>
                    <Link
                      href={`/category/${category.slug}`}
                      onClick={() => setOpen(false)}
                      className="block text-sm text-slate-500 transition hover:text-brand-700"
                      style={{ paddingRight: `${depth * 12}px` }}
                    >
                      {depth > 0 && (
                        <span className="ml-1 text-slate-300">↳</span>
                      )}
                      {category.title}
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
