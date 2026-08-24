"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "@/lib/client-api";

type AddToCartButtonProps = {
  productId: number;
  productTitle: string;
  stock?: number;
  variant?: "default" | "card";
};

type Status = "idle" | "loading" | "success" | "error";

function CartPlusIcon() {
  return (
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
      <path d="M3 4h2l2.2 9.4a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 1.9-1.4l1.2-4.1H7" />
      <path d="M14 5h6M17 2v6" />
      <circle cx="9.5" cy="19" r="1" />
      <circle cx="17.5" cy="19" r="1" />
    </svg>
  );
}

function LoadingIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="h-5 w-5 animate-spin"
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2"
        className="opacity-30"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="h-5 w-5"
    >
      <path d="m5 12 4 4L19 6" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
      className="h-5 w-5"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="m9 9 6 6m0-6-6 6" />
    </svg>
  );
}

function CartUnavailableIcon() {
  return (
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
      <path d="M3 4h2l2.2 9.4a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 1.9-1.4l1.2-4.1H7" />
      <circle cx="9.5" cy="19" r="1" />
      <circle cx="17.5" cy="19" r="1" />
      <path d="m6 3 14 16" />
    </svg>
  );
}

export default function AddToCartButton({
  productId,
  productTitle,
  stock,
  variant = "default",
}: AddToCartButtonProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [feedback, setFeedback] = useState("");
  const adding = useRef(false);
  // Some older/cached list payloads do not include stock. Only a known zero is
  // unavailable; the cart API remains the source of truth for final validation.
  const outOfStock = stock === 0;
  const loading = status === "loading";

  useEffect(() => {
    if (status !== "success" && status !== "error") return;
    const timer = window.setTimeout(() => {
      setStatus("idle");
      setFeedback("");
    }, status === "success" ? 2000 : 4000);
    return () => window.clearTimeout(timer);
  }, [status]);

  async function addToCart() {
    if (adding.current || outOfStock) return;
    adding.current = true;
    setStatus("loading");
    setFeedback("در حال افزودن به سبد خرید");

    const result = await api.post("/api/cart/items", {
      productId,
      qty: 1,
    });

    if (!result.ok) {
      adding.current = false;
      setStatus("error");
      setFeedback(result.error ?? "خطا در افزودن به سبد خرید");
      return;
    }

    adding.current = false;
    setStatus("success");
    setFeedback("به سبد خرید اضافه شد");
    window.dispatchEvent(new CustomEvent("cart:updated"));
  }

  const label = outOfStock
    ? `${productTitle} ناموجود است`
    : loading
      ? `در حال افزودن ${productTitle} به سبد خرید`
      : status === "success"
        ? `${productTitle} به سبد خرید اضافه شد`
        : status === "error"
          ? `${feedback}؛ تلاش دوباره برای افزودن ${productTitle}`
          : `افزودن ${productTitle} به سبد خرید`;

  const colorClass = outOfStock
    ? "bg-slate-100 text-slate-400"
    : status === "success"
      ? "bg-brand-50 text-brand-700 ring-1 ring-brand-200 hover:bg-brand-100"
      : status === "error"
        ? "bg-red-50 text-red-600 ring-1 ring-red-100 hover:bg-red-100"
        : "bg-brand-600 text-white shadow-sm hover:bg-brand-700";
  const sizeClass =
    variant === "card"
      ? "h-9 w-9 rounded-lg"
      : "h-9 w-9 rounded-xl sm:h-10 sm:w-10";

  return (
    <div className="relative z-10 shrink-0">
      <button
        type="button"
        onClick={addToCart}
        disabled={loading || outOfStock}
        aria-label={label}
        aria-busy={loading || undefined}
        title={label}
        className={`grid place-items-center transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:cursor-not-allowed disabled:opacity-60 ${sizeClass} ${colorClass}`}
      >
        {loading ? (
          <LoadingIcon />
        ) : status === "success" ? (
          <CheckIcon />
        ) : status === "error" ? (
          <ErrorIcon />
        ) : outOfStock ? (
          <CartUnavailableIcon />
        ) : (
          <CartPlusIcon />
        )}
      </button>
      {(status === "success" || status === "error") &&
        typeof document !== "undefined" &&
        createPortal(
          <span
            role="status"
            aria-live="polite"
            className={`pointer-events-none fixed bottom-5 left-1/2 z-[100] w-max max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-lg px-3 py-2 text-center text-xs leading-5 text-white shadow-lg ${
              status === "success" ? "bg-brand-700" : "bg-red-600"
            }`}
          >
            {feedback}
          </span>,
          document.body
        )}
      <span className="sr-only" aria-live="polite">
        {loading ? feedback : ""}
      </span>
    </div>
  );
}
