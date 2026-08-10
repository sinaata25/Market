"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/client-api";
import type { Brand } from "@/lib/products";

export default function BrandMenu() {
  const menuRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [brands, setBrands] = useState<Brand[]>([]);

  useEffect(() => {
    let ignore = false;
    api.get<{ brands: Brand[] }>("/api/brands").then((response) => {
      if (!ignore && response.ok && response.data) {
        setBrands(response.data.brands);
      }
    });
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
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
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="product-brand-menu"
        aria-haspopup="menu"
        className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition ${
          open
            ? "bg-brand-50 text-brand-700"
            : "text-slate-700 hover:bg-slate-50"
        }`}
      >
        <span aria-hidden="true">🏷️</span>
        <span>برندها</span>
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

      {open && (
        <div
          id="product-brand-menu"
          className="absolute right-0 top-full z-50 pt-2"
        >
          <div className="w-80 overflow-hidden rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_18px_50px_-16px_rgba(15,23,42,0.35)]">
            <p className="border-b border-slate-100 px-2 pb-3 text-xs font-bold text-slate-700">
              انتخاب بر اساس برند
            </p>
            {brands.length === 0 ? (
              <p className="px-2 py-5 text-center text-xs text-slate-400">
                برند فعالی برای نمایش وجود ندارد
              </p>
            ) : (
              <ul className="mt-2 grid max-h-80 grid-cols-2 gap-1 overflow-y-auto">
                {brands.map((brand) => (
                  <li key={brand.slug}>
                    <Link
                      href={`/brand/${brand.slug}`}
                      onClick={() => setOpen(false)}
                      className="flex min-h-11 items-center gap-2 rounded-xl px-2 py-2 text-xs text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
                    >
                      <span className="grid h-7 w-7 shrink-0 place-items-center overflow-hidden rounded-lg bg-slate-50 ring-1 ring-slate-100">
                        {brand.logo ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={brand.logo}
                            alt=""
                            className="h-5 w-5 object-contain"
                          />
                        ) : (
                          <span aria-hidden="true" className="text-sm">
                            🏷️
                          </span>
                        )}
                      </span>
                      <span className="truncate">{brand.name}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
