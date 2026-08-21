"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { Product } from "@/lib/products";
import { useCompare } from "@/lib/compare";

// دکمه‌ی افزودن/حذف محصول از مقایسه — کاملاً سمت کلاینت (localStorage)
export default function CompareButton({ product }: { product: Product }) {
  const { items, add, remove, check } = useCompare();
  const [feedback, setFeedback] = useState("");

  const active = items.some((item) => item.id === product.id);
  const availability = active ? { ok: true as const } : check(product);
  const disabled = !active && !availability.ok;

  useEffect(() => {
    if (!feedback) return;
    const timer = window.setTimeout(() => setFeedback(""), 3000);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  function toggle() {
    if (active) {
      remove(product.id);
      return;
    }
    const result = add(product);
    if (!result.ok) setFeedback(result.reason ?? "افزودن به مقایسه امکان‌پذیر نیست");
  }

  const label = active
    ? `حذف ${product.title} از مقایسه`
    : disabled
      ? (availability.reason ?? `افزودن ${product.title} به مقایسه امکان‌پذیر نیست`)
      : `افزودن ${product.title} به مقایسه`;

  return (
    <div className="relative z-10 shrink-0">
      <button
        type="button"
        onClick={toggle}
        disabled={disabled}
        aria-pressed={active}
        aria-label={label}
        title={label}
        className={`grid h-10 w-10 place-items-center rounded-xl border text-base transition disabled:cursor-not-allowed disabled:opacity-50 sm:h-11 sm:w-11 ${
          active
            ? "border-brand-300 bg-brand-50 text-brand-700"
            : "border-slate-200 bg-white text-slate-500 hover:border-brand-200"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="h-5 w-5"
        >
          <rect x="3" y="4" width="7" height="16" rx="1.5" />
          <rect x="14" y="4" width="7" height="16" rx="1.5" />
          {active && <path d="m6 12 1.8 1.8L10 10" />}
        </svg>
      </button>
      {feedback &&
        typeof document !== "undefined" &&
        createPortal(
          <span
            role="status"
            aria-live="polite"
            className="pointer-events-none fixed bottom-5 left-1/2 z-[100] w-max max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-lg bg-red-600 px-3 py-2 text-center text-xs leading-5 text-white shadow-lg"
          >
            {feedback}
          </span>,
          document.body
        )}
    </div>
  );
}
