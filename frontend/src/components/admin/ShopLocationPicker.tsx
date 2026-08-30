"use client";

import dynamic from "next/dynamic";
import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/client-api";

/**
 * انتخاب موقعیت فروشگاه برای «مدیریت فوتر».
 *
 * کتابخانه‌ی نقشه فقط اینجا و به‌صورت پویا بارگذاری می‌شود؛ بقیه‌ی داشبورد و
 * کل فروشگاه از آن بی‌خبرند. جست‌وجو و نشانی‌یابی معکوس از API خود پروژه
 * می‌آیند، پس هیچ کلید یا سرویس‌دهنده‌ای در کد فرانت نیست.
 */
const LocationMap = dynamic(() => import("./LocationMap"), {
  ssr: false,
  loading: () => (
    <div className="grid h-72 w-full place-items-center rounded-xl border border-slate-200 bg-slate-50 text-sm text-slate-400 sm:h-80">
      در حال بارگذاری نقشه...
    </div>
  ),
});

export type ShopLocationValues = {
  address: string;
  latitude: string;
  longitude: string;
  showMap: boolean;
  mapZoom: string;
  mapsPlaceUrl: string;
};

type GeocodeResult = {
  label: string;
  latitude: string;
  longitude: string;
};

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white disabled:opacity-60";

/** مختصات فرم به عدد، یا null اگر خالی/نامعتبر باشد */
function parseCoordinate(value: string, limit: number): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || Math.abs(parsed) > limit) return null;
  return parsed;
}

/** ۶ رقم اعشار ≈ دقت ۱۱ سانتی‌متر؛ بیشتر از آن فقط نویز است */
function formatCoordinate(value: number): string {
  return String(Number(value.toFixed(6)));
}

export default function ShopLocationPicker({
  values,
  onChange,
  disabled = false,
}: {
  values: ShopLocationValues;
  onChange: (patch: Partial<ShopLocationValues>) => void;
  disabled?: boolean;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeocodeResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [lookingUp, setLookingUp] = useState(false);
  const [notice, setNotice] = useState("");
  const requestId = useRef(0);

  const latitude = parseCoordinate(values.latitude, 90);
  const longitude = parseCoordinate(values.longitude, 180);
  const zoom = Number(values.mapZoom) || 15;
  const hasCoordinates = latitude !== null && longitude !== null;

  const lookUpAddress = useCallback(
    async (nextLatitude: number, nextLongitude: number) => {
      const id = ++requestId.current;
      setLookingUp(true);
      const response = await api.get<{ address: string | null }>(
        `/api/admin/footer/geocode/reverse?lat=${nextLatitude}&lng=${nextLongitude}`
      );
      if (id !== requestId.current) return;
      setLookingUp(false);
      if (!response.ok) {
        setNotice(response.error ?? "دریافت نشانی انجام نشد");
        return;
      }
      const address = response.data?.address;
      if (address) {
        onChange({ address });
        setNotice("نشانی از نقشه پر شد؛ می‌توانید ویرایشش کنید.");
      } else {
        setNotice("برای این نقطه نشانی‌ای پیدا نشد");
      }
    },
    [onChange]
  );

  const pick = useCallback(
    (nextLatitude: number, nextLongitude: number) => {
      onChange({
        latitude: formatCoordinate(nextLatitude),
        longitude: formatCoordinate(nextLongitude),
      });
      setNotice("");
      // نشانی نوشته‌شده‌ی مدیر هرگز بازنویسی نمی‌شود؛ فقط جای خالی پر می‌گردد
      if (!values.address.trim()) {
        void lookUpAddress(nextLatitude, nextLongitude);
      }
    },
    [lookUpAddress, onChange, values.address]
  );

  const changeZoom = useCallback(
    (nextZoom: number) => onChange({ mapZoom: String(nextZoom) }),
    [onChange]
  );

  async function runSearch(event: React.FormEvent) {
    event.preventDefault();
    const term = query.trim();
    if (!term || searching) return;
    setSearching(true);
    setNotice("");
    const response = await api.get<{ results: GeocodeResult[] }>(
      `/api/admin/footer/geocode/search?q=${encodeURIComponent(term)}`
    );
    setSearching(false);
    if (!response.ok) {
      setResults([]);
      setNotice(response.error ?? "جست‌وجوی نشانی انجام نشد");
      return;
    }
    const found = response.data?.results ?? [];
    setResults(found);
    if (!found.length) setNotice("نتیجه‌ای پیدا نشد؛ می‌توانید روی نقشه کلیک کنید.");
  }

  function chooseResult(result: GeocodeResult) {
    onChange({
      latitude: result.latitude,
      longitude: result.longitude,
      address: result.label,
    });
    setResults([]);
    setQuery("");
    setNotice("");
  }

  function clearLocation() {
    onChange({ latitude: "", longitude: "" });
    setNotice("موقعیت پاک شد؛ برای حذف کامل، ذخیره کنید.");
  }

  return (
    <div className="space-y-4">
      <form onSubmit={runSearch} className="flex flex-wrap gap-2">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={disabled}
          placeholder="جست‌وجوی نشانی یا نام مکان..."
          className={`${INPUT_CLASS} min-w-0 flex-1 basis-56`}
        />
        <button
          type="submit"
          disabled={disabled || searching || !query.trim()}
          className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-600 transition hover:border-brand-400 disabled:opacity-50"
        >
          {searching ? "در حال جست‌وجو..." : "جست‌وجو"}
        </button>
      </form>

      {results.length > 0 && (
        <ul className="max-h-56 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200">
          {results.map((result) => (
            <li key={`${result.latitude},${result.longitude}`}>
              <button
                type="button"
                onClick={() => chooseResult(result)}
                className="block w-full px-3 py-2.5 text-right text-xs leading-6 text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
              >
                {result.label}
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="text-[11px] leading-6 text-slate-400">
        روی نقشه کلیک کنید تا نشانگر همان‌جا قرار بگیرد، یا نشانگر را بکشید تا
        دقیق‌تر شود. مختصات را دستی هم می‌توانید وارد کنید.
      </p>

      <LocationMap
        latitude={latitude}
        longitude={longitude}
        zoom={zoom}
        onPick={pick}
        onZoomChange={changeZoom}
      />

      {notice && <p className="text-[11px] text-slate-500">{notice}</p>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label>
          <span className="mb-1.5 block text-xs text-slate-600">عرض جغرافیایی</span>
          <input
            dir="ltr"
            inputMode="decimal"
            disabled={disabled}
            value={values.latitude}
            onChange={(event) => onChange({ latitude: event.target.value })}
            placeholder="35.715298"
            className={`${INPUT_CLASS} font-num`}
          />
        </label>
        <label>
          <span className="mb-1.5 block text-xs text-slate-600">طول جغرافیایی</span>
          <input
            dir="ltr"
            inputMode="decimal"
            disabled={disabled}
            value={values.longitude}
            onChange={(event) => onChange({ longitude: event.target.value })}
            placeholder="51.404343"
            className={`${INPUT_CLASS} font-num`}
          />
        </label>
        <label className="md:col-span-2">
          <span className="mb-1.5 block text-xs text-slate-600">
            نشانی فروشگاه (در فوتر و کنار نقشه نمایش داده می‌شود)
          </span>
          <textarea
            rows={2}
            maxLength={300}
            disabled={disabled}
            value={values.address}
            onChange={(event) => onChange({ address: event.target.value })}
            className={INPUT_CLASS}
          />
        </label>
        <label>
          <span className="mb-1.5 block text-xs text-slate-600">
            بزرگ‌نمایی نقشه (۱ تا ۲۱)
          </span>
          <input
            type="number"
            min={1}
            max={21}
            disabled={disabled}
            value={values.mapZoom}
            onChange={(event) => onChange({ mapZoom: event.target.value })}
            className={INPUT_CLASS}
          />
        </label>
        <label>
          <span className="mb-1.5 block text-xs text-slate-600">
            پیوند صفحه‌ی گوگل مپس (اختیاری)
          </span>
          <input
            dir="ltr"
            disabled={disabled}
            value={values.mapsPlaceUrl}
            onChange={(event) => onChange({ mapsPlaceUrl: event.target.value })}
            placeholder="https://maps.app.goo.gl/..."
            className={INPUT_CLASS}
          />
          <span className="mt-1 block text-[11px] text-slate-400">
            جای‌گزین پیوند «مشاهده روی نقشه». مسیریابی همیشه از مختصات بالا
            ساخته می‌شود.
          </span>
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={disabled || !hasCoordinates || lookingUp}
          onClick={() => hasCoordinates && lookUpAddress(latitude, longitude)}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-600 transition hover:border-brand-400 disabled:opacity-40"
        >
          {lookingUp ? "در حال دریافت..." : "دریافت نشانی این نقطه"}
        </button>
        <button
          type="button"
          disabled={disabled || !hasCoordinates}
          onClick={clearLocation}
          className="rounded-lg border border-red-100 px-3 py-1.5 text-xs text-red-600 disabled:opacity-40"
        >
          پاک کردن موقعیت
        </button>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            disabled={disabled}
            checked={values.showMap}
            onChange={(event) => onChange({ showMap: event.target.checked })}
          />
          نقشه در فوتر نمایش داده شود
        </label>
      </div>

      {values.showMap && !hasCoordinates && (
        <p className="rounded-xl bg-amber-50 px-4 py-2.5 text-[11px] text-amber-700">
          تا وقتی مختصاتی ذخیره نشده باشد، نقشه در فوتر نمایش داده نمی‌شود.
        </p>
      )}
    </div>
  );
}
