"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/client-api";

// دکمه افزودن/حذف علاقه‌مندی — برای کاربر مهمان به صفحه ورود می‌برد
export default function FavoriteButton({ productId }: { productId: number }) {
  const router = useRouter();
  const [favorited, setFavorited] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get<{ favorited: boolean }>(`/api/auth/favorites/${productId}`)
      .then((res) => {
        if (res.ok && res.data) {
          setLoggedIn(true);
          setFavorited(res.data.favorited);
        }
      });
  }, [productId]);

  async function toggle() {
    if (!loggedIn) {
      const currentPath = `${window.location.pathname}${window.location.search}`;
      router.push(`/login?next=${encodeURIComponent(currentPath)}`);
      return;
    }
    setBusy(true);
    const res = await api.post<{ favorited: boolean }>(
      "/api/auth/favorites",
      { productId }
    );
    setBusy(false);
    if (res.ok && res.data) setFavorited(res.data.favorited);
  }

  return (
    <button
      onClick={toggle}
      disabled={busy}
      title={favorited ? "حذف از علاقه‌مندی‌ها" : "افزودن به علاقه‌مندی‌ها"}
      className={`grid h-10 w-10 place-items-center rounded-xl border text-base transition disabled:opacity-50 sm:h-11 sm:w-11 ${
        favorited
          ? "border-red-200 bg-red-50"
          : "border-slate-200 bg-white hover:border-red-200"
      }`}
    >
      {favorited ? "❤️" : "🤍"}
    </button>
  );
}
