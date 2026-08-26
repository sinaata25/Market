"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { api, subscribeAuthChanged } from "@/lib/client-api";

type FavoriteStatus = "idle" | "loading" | "ready" | "guest" | "error";

type FavoriteSnapshot = {
  ids: ReadonlySet<number>;
  status: FavoriteStatus;
};

type FavoriteButtonProps = {
  productId: number;
  productTitle?: string;
  variant?: "default" | "card";
  onChange?: (favorited: boolean) => void;
};

const emptyIds = new Set<number>();
const serverSnapshot: FavoriteSnapshot = { ids: emptyIds, status: "idle" };
let favoriteSnapshot: FavoriteSnapshot = serverSnapshot;
let favoriteRequest: Promise<void> | null = null;
let requestVersion = 0;
let authSubscriptionStarted = false;
const listeners = new Set<() => void>();

function emitChange() {
  listeners.forEach((listener) => listener());
}

function updateSnapshot(next: FavoriteSnapshot) {
  favoriteSnapshot = next;
  emitChange();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function loadFavorites(): Promise<void> {
  if (
    favoriteSnapshot.status === "ready" ||
    favoriteSnapshot.status === "guest"
  ) {
    return Promise.resolve();
  }
  if (favoriteRequest) return favoriteRequest;

  updateSnapshot({ ...favoriteSnapshot, status: "loading" });
  const version = requestVersion;
  const request = api
    .get<{ favorites: { id: number }[] }>("/api/auth/favorites")
    .then((res) => {
      if (version !== requestVersion) return;

      if (res.ok && res.data) {
        updateSnapshot({
          ids: new Set(res.data.favorites.map((product) => product.id)),
          status: "ready",
        });
        return;
      }

      updateSnapshot({
        ids: emptyIds,
        status: res.status === 401 || res.status === 403 ? "guest" : "error",
      });
    })
    .finally(() => {
      if (favoriteRequest === request) favoriteRequest = null;
    });
  favoriteRequest = request;

  return request;
}

function ensureAuthSubscription() {
  if (authSubscriptionStarted) return;
  authSubscriptionStarted = true;
  subscribeAuthChanged(() => {
    requestVersion += 1;
    favoriteRequest = null;
    updateSnapshot(serverSnapshot);
    void loadFavorites();
  });
}

// دکمه افزودن/حذف علاقه‌مندی — برای کاربر مهمان به صفحه ورود می‌برد
export default function FavoriteButton({
  productId,
  productTitle,
  variant = "default",
  onChange,
}: FavoriteButtonProps) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const snapshot = useSyncExternalStore(
    subscribe,
    () => favoriteSnapshot,
    () => serverSnapshot
  );
  const favorited = snapshot.ids.has(productId);

  useEffect(() => {
    ensureAuthSubscription();
    void loadFavorites();
  }, []);

  async function toggle() {
    if (busy) return;
    setBusy(true);

    if (
      favoriteSnapshot.status !== "ready" &&
      favoriteSnapshot.status !== "guest"
    ) {
      await loadFavorites();
    }

    if (favoriteSnapshot.status === "guest") {
      const currentPath = `${window.location.pathname}${window.location.search}`;
      router.push(`/login?next=${encodeURIComponent(currentPath)}`);
      setBusy(false);
      return;
    }

    if (favoriteSnapshot.status !== "ready") {
      setBusy(false);
      return;
    }

    const res = await api.post<{ favorited: boolean }>(
      "/api/auth/favorites",
      { productId }
    );
    setBusy(false);
    if (res.ok && res.data) {
      const ids = new Set(favoriteSnapshot.ids);
      if (res.data.favorited) ids.add(productId);
      else ids.delete(productId);
      updateSnapshot({ ids, status: "ready" });
      onChange?.(res.data.favorited);
      return;
    }

    if (res.status === 401 || res.status === 403) {
      updateSnapshot({ ids: emptyIds, status: "guest" });
      const currentPath = `${window.location.pathname}${window.location.search}`;
      router.push(`/login?next=${encodeURIComponent(currentPath)}`);
    }
  }

  const subject = productTitle ? ` «${productTitle}»` : " محصول";
  const label = favorited
    ? `حذف${subject} از علاقه‌مندی‌ها`
    : snapshot.status === "loading"
      ? `در حال بررسی علاقه‌مندی${subject}`
      : snapshot.status === "error"
        ? `تلاش دوباره برای افزودن${subject} به علاقه‌مندی‌ها`
        : `افزودن${subject} به علاقه‌مندی‌ها`;
  const sizeClass =
    variant === "card"
      ? "h-8 w-8 rounded-full shadow-sm backdrop-blur-sm"
      : "h-10 w-10 rounded-xl sm:h-11 sm:w-11";
  const colorClass = favorited
    ? "border-red-200 bg-red-50/95 text-red-600 hover:bg-red-100"
    : variant === "card"
      ? "border-white/80 bg-white/95 text-slate-500 hover:border-red-200 hover:text-red-600"
      : "border-slate-200 bg-white text-slate-500 hover:border-red-200 hover:text-red-600";

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      aria-label={label}
      aria-pressed={favorited}
      aria-busy={busy || snapshot.status === "loading" || undefined}
      title={label}
      className={`grid place-items-center border transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 disabled:cursor-wait disabled:opacity-60 ${sizeClass} ${colorClass}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill={favorited ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className={`h-5 w-5 ${busy ? "animate-pulse" : ""}`}
      >
        <path d="M20.8 4.7a5.5 5.5 0 0 0-7.8 0L12 5.8l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.4 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" />
      </svg>
    </button>
  );
}
