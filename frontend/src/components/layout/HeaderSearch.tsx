"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export default function HeaderSearch() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentSearch =
    pathname.startsWith("/products") || pathname.startsWith("/category/")
      ? (searchParams.get("search") ?? "").slice(0, 200)
      : "";

  return (
    <HeaderSearchForm
      key={`${pathname}?search=${currentSearch}`}
      pathname={pathname}
      searchParamsValue={searchParams.toString()}
      currentSearch={currentSearch}
    />
  );
}

function HeaderSearchForm({
  pathname,
  searchParamsValue,
  currentSearch,
}: {
  pathname: string;
  searchParamsValue: string;
  currentSearch: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [query, setQuery] = useState(currentSearch);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    const params = new URLSearchParams();
    if (value) params.set("search", value);
    startTransition(() => {
      router.push(`/products${params.size ? `?${params.toString()}` : ""}`);
    });
  }

  function clear() {
    setQuery("");
    if (!currentSearch || (!pathname.startsWith("/products") && !pathname.startsWith("/category/"))) {
      return;
    }
    const params = new URLSearchParams(searchParamsValue);
    params.delete("search");
    params.delete("page");
    startTransition(() => {
      router.push(`${pathname}${params.size ? `?${params.toString()}` : ""}`);
    });
  }

  return (
    <form onSubmit={submit} role="search" className="relative" aria-label="جستجو در فروشگاه">
      <input
        aria-label="عبارت جستجو"
        name="search"
        type="search"
        maxLength={200}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="جستجو در گروه صنعتی توانا..."
        className="h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-11 pl-20 text-base outline-none transition focus:border-brand-400 focus:bg-white sm:text-sm"
      />
      <button
        type="submit"
        disabled={pending}
        aria-label="اجرای جستجو"
        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 disabled:opacity-50"
      >
        {pending ? "…" : "🔍"}
      </button>
      {query && (
        <button
          type="button"
          onClick={clear}
          aria-label="پاک کردن جستجو"
          className="absolute left-3 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          پاک کردن
        </button>
      )}
    </form>
  );
}

export function HeaderSearchFallback() {
  return (
    <div className="relative">
      <input
        aria-label="جستجو در فروشگاه"
        disabled
        placeholder="جستجو در گروه صنعتی توانا..."
        className="h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-slate-50 py-2.5 pr-11 pl-4 text-base sm:text-sm"
      />
      <span aria-hidden className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">🔍</span>
    </div>
  );
}
