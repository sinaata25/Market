"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/client-api";
import { faDate } from "@/components/admin/ui";

type Profile = {
  user: {
    id: number;
    phone: string;
    name: string | null;
    dateJoined: string;
  };
};

const inputCls =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";

export default function AccountInfo() {
  const router = useRouter();
  const [profile, setProfile] = useState<Profile["user"] | null>(null);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(
    null
  );

  useEffect(() => {
    api.get<Profile>("/api/auth/profile").then((res) => {
      if (res.ok && res.data) {
        setProfile(res.data.user);
        setName(res.data.user.name ?? "");
      }
    });
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    const res = await api.patch<{ user: { name: string | null } }>(
      "/api/auth/profile",
      { name }
    );
    setSaving(false);
    if (res.ok) {
      setMessage({ ok: true, text: "اطلاعات ذخیره شد ✅" });
      router.refresh();
    } else {
      setMessage({ ok: false, text: res.error ?? "خطا در ذخیره" });
    }
  }

  async function logout() {
    await api.post("/api/auth/logout");
    window.dispatchEvent(new CustomEvent("cart:updated"));
    router.push("/");
    router.refresh();
  }

  if (!profile) {
    return (
      <div className="grid min-h-[40vh] place-items-center text-sm text-slate-400">
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-bold text-slate-800">اطلاعات حساب</h1>

      <form
        onSubmit={save}
        className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5"
      >
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-600">
            نام و نام خانوادگی
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="مثلا: سینا عطایی"
            className={inputCls}
          />
          <p className="mt-1.5 text-[11px] text-slate-400">
            این نام در دیدگاه‌های شما و سفارش‌ها نمایش داده می‌شود.
          </p>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-600">
            شماره موبایل
          </label>
          <input
            disabled
            dir="ltr"
            value={profile.phone}
            className={`${inputCls} cursor-not-allowed text-center font-num opacity-60`}
          />
          <p className="mt-1.5 text-[11px] text-slate-400">
            شماره موبایل شناسه ورود شماست و قابل تغییر نیست.
          </p>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-600">
            تاریخ عضویت
          </label>
          <input
            disabled
            value={faDate(profile.dateJoined)}
            className={`${inputCls} cursor-not-allowed font-num opacity-60`}
          />
        </div>

        {message && (
          <p
            className={`rounded-xl px-4 py-3 text-xs ${
              message.ok
                ? "bg-emerald-50 text-emerald-700"
                : "bg-red-50 text-red-500"
            }`}
          >
            {message.text}
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="rounded-xl bg-brand-600 px-8 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
        >
          {saving ? "در حال ذخیره..." : "ذخیره تغییرات"}
        </button>
      </form>

      {/* امنیت */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5">
        <h2 className="mb-3 text-sm font-bold text-slate-700">
          امنیت حساب
        </h2>
        <p className="mb-4 text-xs leading-6 text-slate-500">
          ورود به حساب شما با شماره موبایل انجام می‌شود. اگر از دستگاه دیگری
          استفاده کرده‌اید، از حساب خارج شوید.
        </p>
        <button
          onClick={logout}
          className="rounded-xl border border-red-200 bg-red-50 px-5 py-2.5 text-xs font-medium text-red-500 transition hover:bg-red-100"
        >
          خروج از حساب کاربری
        </button>
      </div>
    </div>
  );
}
