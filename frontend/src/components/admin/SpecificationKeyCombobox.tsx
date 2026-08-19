"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/client-api";
import type { SpecificationKey } from "@/components/admin/specification-types";

type SpecificationListResponse = {
  specifications: SpecificationKey[];
};

function normalizedName(value: string) {
  return value
    .normalize("NFKC")
    .replace(/[يى]/gu, "ی")
    .replace(/ك/gu, "ک")
    .replace(/[\u00a0\u200c]/gu, " ")
    .replace(/\s+/gu, " ")
    .trim()
    .toLocaleLowerCase("fa-IR");
}

export default function SpecificationKeyCombobox({
  id,
  value,
  excludedIds,
  onChange,
  hasError = false,
  disabled = false,
}: {
  id: string;
  value: SpecificationKey | null;
  excludedIds: number[];
  onChange: (value: SpecificationKey | null) => void;
  hasError?: boolean;
  disabled?: boolean;
}) {
  const listboxId = `${id}-listbox`;
  const [query, setQuery] = useState(value?.name ?? "");
  const [results, setResults] = useState<SpecificationKey[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const [hasExactMatch, setHasExactMatch] = useState(false);
  const [searchReady, setSearchReady] = useState(false);
  const requestId = useRef(0);
  const queryVersion = useRef(0);
  const createInFlight = useRef(false);
  const mounted = useRef(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  const excludedIdsSignature = [...excludedIds]
    .sort((first, second) => first - second)
    .join(",");

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (!open) return;
    const currentRequest = ++requestId.current;
    const excludedIdsForRequest = new Set(
      excludedIdsSignature
        ? excludedIdsSignature.split(",").map((item) => Number(item))
        : []
    );
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams();
      if (query.trim()) params.set("search", query.trim());
      const suffix = params.toString();
      api
        .get<SpecificationListResponse>(
          `/api/admin/specifications${suffix ? `?${suffix}` : ""}`
        )
        .then((result) => {
          if (currentRequest !== requestId.current) return;
          if (!result.ok) {
            setResults([]);
            setHasExactMatch(false);
            setSearchReady(false);
            setMessage(result.error ?? "دریافت مشخصه‌ها انجام نشد");
          } else {
            const all = result.data?.specifications ?? [];
            const normalizedQuery = normalizedName(query);
            setHasExactMatch(
              Boolean(normalizedQuery) &&
                all.some(
                  (specification) =>
                    normalizedName(specification.name) === normalizedQuery
                )
            );
            setResults(
              all.filter(
                (specification) =>
                  specification.id === value?.id ||
                  !excludedIdsForRequest.has(specification.id)
              )
            );
            setSearchReady(true);
          }
          setActiveIndex(-1);
          setLoading(false);
        });
    }, 220);

    return () => {
      window.clearTimeout(timer);
      if (requestId.current === currentRequest) requestId.current += 1;
    };
  }, [excludedIdsSignature, open, query, value?.id]);

  useEffect(() => {
    if (!open) return;
    function closeWhenClickedOutside(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    }
    document.addEventListener("pointerdown", closeWhenClickedOutside, true);
    return () =>
      document.removeEventListener("pointerdown", closeWhenClickedOutside, true);
  }, [open]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      requestId.current += 1;
    };
  }, []);

  const trimmedQuery = query.trim();
  const canCreate =
    Boolean(trimmedQuery) && searchReady && !hasExactMatch && !loading;
  const activeOptionId =
    activeIndex >= 0 && activeIndex < results.length
      ? `${listboxId}-option-${results[activeIndex].id}`
      : undefined;

  useEffect(() => {
    if (!activeOptionId) return;
    document
      .getElementById(activeOptionId)
      ?.scrollIntoView({ block: "nearest" });
  }, [activeOptionId]);

  function choose(specification: SpecificationKey) {
    queryVersion.current += 1;
    requestId.current += 1;
    onChangeRef.current(specification);
    setQuery(specification.name);
    setMessage("");
    setOpen(false);
    setActiveIndex(-1);
  }

  async function createKey() {
    const name = trimmedQuery;
    if (!name || creating || createInFlight.current) return;
    createInFlight.current = true;
    const startedAtQueryVersion = queryVersion.current;
    setCreating(true);
    setMessage("");
    const result = await api.post<{ specification: SpecificationKey }>(
      "/api/admin/specifications",
      { name }
    );
    createInFlight.current = false;
    if (!mounted.current) return;
    setCreating(false);
    if (startedAtQueryVersion !== queryVersion.current) return;
    if (!result.ok || !result.data) {
      setMessage(result.error ?? "ساخت مشخصه انجام نشد");
      return;
    }
    choose(result.data.specification);
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        id={id}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-activedescendant={activeOptionId}
        aria-invalid={hasError || undefined}
        autoComplete="off"
        disabled={disabled}
        value={query}
        onFocus={() => {
          setOpen(true);
          setLoading(true);
          setSearchReady(false);
        }}
        onBlur={(event) => {
          const nextTarget = event.relatedTarget;
          if (
            !nextTarget ||
            !containerRef.current?.contains(nextTarget as Node)
          ) {
            setOpen(false);
            setActiveIndex(-1);
          }
        }}
        onChange={(event) => {
          const nextQuery = event.target.value;
          queryVersion.current += 1;
          requestId.current += 1;
          setQuery(nextQuery);
          setOpen(true);
          setLoading(true);
          setSearchReady(false);
          setResults([]);
          setHasExactMatch(false);
          setActiveIndex(-1);
          setMessage("");
          if (value && nextQuery !== value.name) onChangeRef.current(null);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            if (loading) return;
            setActiveIndex((current) =>
              results.length ? Math.min(current + 1, results.length - 1) : -1
            );
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
            if (loading) return;
            setActiveIndex((current) =>
              results.length ? Math.max(current - 1, 0) : -1
            );
          } else if (event.key === "Enter" && open) {
            if (activeIndex >= 0 && results[activeIndex]) {
              event.preventDefault();
              choose(results[activeIndex]);
            } else if (canCreate) {
              event.preventDefault();
              void createKey();
            }
          } else if (event.key === "Escape") {
            setOpen(false);
            setActiveIndex(-1);
          }
        }}
        className={`w-full rounded-xl border bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:bg-white disabled:cursor-not-allowed disabled:opacity-60 ${
          hasError
            ? "border-red-300 focus:border-red-400"
            : "border-slate-200 focus:border-brand-400"
        }`}
        placeholder="نام مشخصه را جستجو کنید..."
      />

      {open && !disabled && (
        <div
          id={listboxId}
          role="listbox"
          aria-label="مشخصه‌های موجود"
          className="absolute inset-x-0 z-30 mt-1 max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg"
        >
          {loading ? (
            <p className="px-3 py-3 text-xs text-slate-400">
              در حال جستجو...
            </p>
          ) : results.length > 0 ? (
            results.map((specification, index) => (
              <button
                key={specification.id}
                id={`${listboxId}-option-${specification.id}`}
                type="button"
                role="option"
                tabIndex={-1}
                aria-selected={value?.id === specification.id}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(specification)}
                className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-right text-xs transition ${
                  activeIndex === index || value?.id === specification.id
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                <span>{specification.name}</span>
                <span className="font-mono text-[10px] text-slate-300" dir="ltr">
                  {specification.slug}
                </span>
              </button>
            ))
          ) : (
            <p className="px-3 py-3 text-xs text-slate-400">
              مشخصه‌ای پیدا نشد.
            </p>
          )}

          {canCreate && (
            <button
              type="button"
              disabled={creating}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => void createKey()}
              className="mt-1 w-full rounded-lg border-t border-slate-100 px-3 py-2.5 text-right text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50"
            >
              {creating ? "در حال ساخت..." : `+ ایجاد مشخصه «${trimmedQuery}»`}
            </button>
          )}

          {hasExactMatch &&
            results.length === 0 &&
            Boolean(excludedIdsSignature) && (
            <p className="px-3 py-2 text-[11px] text-amber-600">
              این مشخصه قبلاً برای محصول انتخاب شده است.
            </p>
          )}

          {message && (
            <p className="px-3 py-2 text-[11px] text-red-500" aria-live="polite">
              {message}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
