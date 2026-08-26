"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { EmptyRow, faNum } from "@/components/admin/ui";
import type { SpecificationKey } from "@/components/admin/specification-types";
import { api } from "@/lib/client-api";

type ManagedSpecificationKey = SpecificationKey & {
  productCount: number;
};

type SpecificationListResponse = {
  specifications: ManagedSpecificationKey[];
};

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";

export default function AdminSpecificationsPage() {
  const [specifications, setSpecifications] = useState<
    ManagedSpecificationKey[]
  >([]);
  const [search, setSearch] = useState("");
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<ManagedSpecificationKey | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const requestId = useRef(0);
  const searchRef = useRef("");
  const messageTimer = useRef<number | null>(null);
  const formSection = useRef<HTMLElement>(null);

  const notify = useCallback((text: string) => {
    setMessage(text);
    if (messageTimer.current) window.clearTimeout(messageTimer.current);
    messageTimer.current = window.setTimeout(() => setMessage(""), 5000);
  }, []);

  const load = useCallback(
    async (query: string) => {
      const currentRequest = ++requestId.current;
      const params = new URLSearchParams();
      if (query.trim()) params.set("search", query.trim());
      const suffix = params.toString();
      const result = await api.get<SpecificationListResponse>(
        `/api/admin/specifications${suffix ? `?${suffix}` : ""}`
      );
      if (currentRequest !== requestId.current) return;
      if (result.ok) setSpecifications(result.data?.specifications ?? []);
      else notify(result.error ?? "دریافت مشخصه‌ها انجام نشد");
      setLoading(false);
    },
    [notify]
  );

  useEffect(() => {
    const timer = window.setTimeout(() => void load(search), 250);
    return () => {
      window.clearTimeout(timer);
      requestId.current += 1;
    };
  }, [load, search]);

  useEffect(
    () => () => {
      if (messageTimer.current) window.clearTimeout(messageTimer.current);
    },
    []
  );

  function resetForm() {
    setName("");
    setEditing(null);
  }

  function startEditing(specification: ManagedSpecificationKey) {
    setEditing(specification);
    setName(specification.name);
    formSection.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedName = name.trim();
    if (!normalizedName) {
      notify("نام مشخصه را وارد کنید");
      return;
    }
    if (saving) return;
    setSaving(true);
    const result = editing
      ? await api.patch<{ specification: ManagedSpecificationKey }>(
          `/api/admin/specifications/${editing.id}`,
          { name: normalizedName }
        )
      : await api.post<{ specification: ManagedSpecificationKey }>(
          "/api/admin/specifications",
          { name: normalizedName }
        );
    setSaving(false);
    if (!result.ok) {
      notify(result.error ?? "ذخیره مشخصه انجام نشد");
      return;
    }
    notify(editing ? "نام مشخصه ویرایش شد ✅" : "مشخصه افزوده شد ✅");
    resetForm();
    setLoading(true);
    await load(searchRef.current);
  }

  async function remove(specification: ManagedSpecificationKey) {
    if (deletingId !== null) return;
    if (specification.productCount > 0) {
      notify(
        `این مشخصه در ${faNum(specification.productCount)} محصول استفاده شده و قابل حذف نیست.`
      );
      return;
    }
    if (
      !window.confirm(
        `مشخصه «${specification.name}» حذف شود؟ این کار قابل بازگشت نیست.`
      )
    ) {
      return;
    }
    setDeletingId(specification.id);
    const result = await api.delete(
      `/api/admin/specifications/${specification.id}`
    );
    setDeletingId(null);
    if (!result.ok) {
      notify(result.error ?? "حذف مشخصه انجام نشد");
      return;
    }
    if (editing?.id === specification.id) resetForm();
    notify("مشخصه حذف شد ✅");
    setLoading(true);
    await load(searchRef.current);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-slate-800">مشخصات محصولات</h1>
        <p className="mt-1 text-xs leading-6 text-slate-400">
          هر مشخصه یک‌بار ساخته می‌شود و می‌تواند با مقدارهای متفاوت در چند محصول
          استفاده شود.
        </p>
      </div>

      {message && (
        <p
          role="status"
          className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs text-white"
        >
          {message}
        </p>
      )}

      <section
        ref={formSection}
        className="scroll-mt-[calc(var(--header-h)+1rem)] rounded-2xl border border-slate-100 bg-white p-5"
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <div>
            <h2 className="font-bold text-slate-700">
              {editing ? `ویرایش «${editing.name}»` : "افزودن مشخصه"}
            </h2>
            {editing && editing.productCount > 0 && (
              <p className="mt-1 text-[11px] leading-5 text-amber-600">
                تغییر نام در همه {faNum(editing.productCount)} محصول استفاده‌کننده
                نمایش داده می‌شود.
              </p>
            )}
          </div>
          {editing && (
            <button
              type="button"
              onClick={resetForm}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              انصراف از ویرایش
            </button>
          )}
        </div>
        <form
          onSubmit={save}
          className="grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end"
        >
          <label>
            <span className="mb-1.5 block text-xs font-medium text-slate-600">
              نام مشخصه
            </span>
            <input
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={INPUT_CLASS}
              placeholder="مثلاً ابعاد، وزن یا توان خروجی"
            />
          </label>
          <button
            disabled={saving}
            className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving
              ? "در حال ذخیره..."
              : editing
                ? "ذخیره تغییرات"
                : "+ افزودن مشخصه"}
          </button>
        </form>
      </section>

      <section className="space-y-3">
        <label className="block sm:max-w-sm">
          <span className="sr-only">جستجوی مشخصه</span>
          <input
            value={search}
            onChange={(event) => {
              const nextSearch = event.target.value;
              searchRef.current = nextSearch;
              setSearch(nextSearch);
              setLoading(true);
            }}
            className={INPUT_CLASS}
            placeholder="جستجوی مشخصه..."
          />
        </label>

        <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
                <th className="px-5 py-3 font-medium">نام مشخصه</th>
                <th className="px-3 py-3 font-medium">نامک</th>
                <th className="px-3 py-3 font-medium">محصولات استفاده‌کننده</th>
                <th className="px-5 py-3 font-medium">عملیات</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading ? (
                <EmptyRow colSpan={4} text="در حال بارگذاری..." />
              ) : specifications.length === 0 ? (
                <EmptyRow colSpan={4} text="مشخصه‌ای یافت نشد" />
              ) : (
                specifications.map((specification) => (
                  <tr key={specification.id} className="hover:bg-slate-50/60">
                    <td className="px-5 py-3 text-xs font-medium text-slate-700">
                      {specification.name}
                    </td>
                    <td
                      dir="ltr"
                      className="px-3 py-3 text-right font-mono text-xs text-slate-400"
                    >
                      {specification.slug}
                    </td>
                    <td className="px-3 py-3 text-xs text-slate-500 font-num">
                      {faNum(specification.productCount)}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3 text-xs">
                        <button
                          type="button"
                          onClick={() => startEditing(specification)}
                          className="text-brand-600 hover:underline"
                        >
                          ویرایش نام
                        </button>
                        <button
                          type="button"
                          disabled={deletingId !== null}
                          onClick={() => void remove(specification)}
                          title={
                            specification.productCount > 0
                              ? "مشخصه استفاده‌شده قابل حذف نیست"
                              : undefined
                          }
                          className={`hover:underline disabled:cursor-not-allowed disabled:text-slate-300 ${
                            specification.productCount > 0
                              ? "text-slate-400"
                              : "text-red-400 hover:text-red-600"
                          }`}
                        >
                          {deletingId === specification.id
                            ? "در حال حذف..."
                            : "حذف"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
