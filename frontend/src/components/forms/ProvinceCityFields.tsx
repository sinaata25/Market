"use client";

import { useEffect, useId, useState } from "react";
import {
  cityOptionLabel,
  locationAfterProvinceChange,
  locationsApi,
  normalizeLocationName,
  resolveLocationOption,
  type CityOption,
  type ProvinceCityValue,
  type ProvinceOption,
} from "@/lib/locations";

type ProvinceLoadState = {
  request: number;
  provinces: ProvinceOption[];
  error: string;
};

type CityLoadState = {
  requestKey: string;
  cities: CityOption[];
  error: string;
};

type Props = ProvinceCityValue & {
  onChange: (value: ProvinceCityValue) => void;
  onClearError?: () => void;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  selectClassName?: string;
  labelClassName?: string;
};

const defaultSelectClassName =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white";
const defaultLabelClassName =
  "mb-1.5 block text-xs text-slate-500";
const LEGACY_PROVINCE_VALUE = "__current_legacy_province__";
const LEGACY_CITY_VALUE = "__current_legacy_city__";

export default function ProvinceCityFields({
  province,
  city,
  provinceId,
  cityId,
  onChange,
  onClearError,
  required = true,
  disabled = false,
  className = "grid gap-3 sm:grid-cols-2",
  selectClassName = defaultSelectClassName,
  labelClassName = defaultLabelClassName,
}: Props) {
  const fieldId = useId();
  const [provinceRequest, setProvinceRequest] = useState(0);
  const [provinceState, setProvinceState] = useState<ProvinceLoadState>({
    request: -1,
    provinces: [],
    error: "",
  });
  const [cityRequest, setCityRequest] = useState(0);
  const [cityState, setCityState] = useState<CityLoadState>({
    requestKey: "",
    cities: [],
    error: "",
  });

  useEffect(() => {
    let active = true;
    const request = provinceRequest;

    locationsApi
      .getProvinces({ force: provinceRequest > 0 })
      .then((result) => {
        if (!active) return;
        if (result.ok && Array.isArray(result.data?.provinces)) {
          setProvinceState({
            request,
            provinces: result.data.provinces,
            error: "",
          });
        } else {
          setProvinceState({
            request,
            provinces: [],
            error: result.error ?? "دریافت فهرست استان‌ها با خطا روبه‌رو شد",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [provinceRequest]);

  const provinceLoading = provinceState.request !== provinceRequest;
  const provinces = provinceLoading ? [] : provinceState.provinces;
  const provinceError = provinceLoading ? "" : provinceState.error;
  const selectedProvince = resolveLocationOption(
    provinces,
    provinceId,
    province
  );
  const selectedProvinceId = selectedProvince?.id ?? "";
  const cityRequestKey = selectedProvinceId
    ? `${selectedProvinceId}:${cityRequest}`
    : "";

  useEffect(() => {
    if (!selectedProvinceId) return;

    let active = true;
    const requestKey = cityRequestKey;
    locationsApi
      .getCities(selectedProvinceId, { force: cityRequest > 0 })
      .then((result) => {
        if (!active) return;
        if (result.ok && Array.isArray(result.data?.cities)) {
          setCityState({
            requestKey,
            cities: result.data.cities,
            error: "",
          });
        } else {
          setCityState({
            requestKey,
            cities: [],
            error: result.error ?? "دریافت فهرست شهرها با خطا روبه‌رو شد",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [cityRequest, cityRequestKey, selectedProvinceId]);

  const cityResponseMatches = Boolean(
    selectedProvinceId && cityState.requestKey === cityRequestKey
  );
  const cityLoading = Boolean(selectedProvinceId) && !cityResponseMatches;
  const cities = cityResponseMatches ? cityState.cities : [];
  const cityError = cityResponseMatches ? cityState.error : "";
  const selectedCity = resolveLocationOption(cities, cityId, city);
  const selectedCityId = selectedCity?.id ?? "";
  const normalizedCurrentCity = normalizeLocationName(city);
  const ambiguousLegacyCity = Boolean(
    !cityId &&
      normalizedCurrentCity &&
      cities.filter(
        (candidate) =>
          normalizeLocationName(candidate.name) === normalizedCurrentCity
      ).length > 1
  );
  const legacyProvince = Boolean(
    province && !provinceLoading && !provinceError && !selectedProvince
  );
  const legacyCity = Boolean(
    selectedProvince && city && !cityLoading && !cityError && !selectedCityId
  );
  const preserveCurrentProvince = Boolean(
    province && !provinceLoading && !selectedProvince
  );
  const preserveCurrentCity = Boolean(
    city && !cityLoading && !selectedCity
  );

  function changeProvince(provinceId: string) {
    if (provinceId === LEGACY_PROVINCE_VALUE) return;
    onClearError?.();
    setCityRequest(0);
    onChange(locationAfterProvinceChange(provinces, provinceId));
  }

  function changeCity(cityId: string) {
    if (cityId === LEGACY_CITY_VALUE) return;
    const selectedCity = cities.find((candidate) => candidate.id === cityId);
    onClearError?.();
    onChange({
      province: selectedProvince?.name ?? "",
      city: selectedCity?.name ?? "",
      provinceId: selectedProvince?.id ?? null,
      cityId: selectedCity?.id ?? null,
    });
  }

  function retryProvinces() {
    onClearError?.();
    setProvinceRequest((request) => request + 1);
  }

  function retryCities() {
    onClearError?.();
    setCityRequest((request) => request + 1);
  }

  const provincePlaceholder = provinceLoading
    ? "در حال دریافت استان‌ها..."
    : provinceError
      ? "دریافت استان‌ها ناموفق بود"
      : legacyProvince
        ? `استان فعلی «${province}»؛ دوباره انتخاب کنید`
        : "انتخاب استان";
  const cityPlaceholder = !selectedProvince
    ? city
      ? `شهر فعلی «${city}»؛ ابتدا استان را انتخاب کنید`
      : "ابتدا استان را انتخاب کنید"
    : cityLoading
      ? "در حال دریافت شهرها..."
      : cityError
        ? "دریافت شهرها ناموفق بود"
        : legacyCity
          ? ambiguousLegacyCity
            ? `شهر فعلی «${city}»؛ شهرستان را مشخص کنید`
            : `شهر فعلی «${city}»؛ دوباره انتخاب کنید`
          : "انتخاب شهر";

  return (
    <div className={className}>
      <div>
        <label htmlFor={`${fieldId}-province`} className={labelClassName}>
          استان {required && "*"}
        </label>
        <select
          id={`${fieldId}-province`}
          required={required}
          disabled={disabled}
          value={
            selectedProvinceId
              ? selectedProvinceId
              : preserveCurrentProvince
                ? LEGACY_PROVINCE_VALUE
                : ""
          }
          onChange={(event) => changeProvince(event.target.value)}
          aria-busy={provinceLoading}
          aria-invalid={Boolean(provinceError || legacyProvince)}
          className={`${selectClassName} cursor-pointer disabled:cursor-not-allowed disabled:opacity-60`}
        >
          <option value="" disabled>
            {provincePlaceholder}
          </option>
          {preserveCurrentProvince && (
            <option value={LEGACY_PROVINCE_VALUE}>{province}</option>
          )}
          {provinces.map((option) => (
            <option key={option.id} value={option.id}>
              {option.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor={`${fieldId}-city`} className={labelClassName}>
          شهر {required && "*"}
        </label>
        <select
          id={`${fieldId}-city`}
          required={required}
          disabled={disabled || !selectedProvince}
          value={
            selectedCityId
              ? selectedCityId
              : preserveCurrentCity
                ? LEGACY_CITY_VALUE
                : ""
          }
          onChange={(event) => changeCity(event.target.value)}
          aria-busy={cityLoading}
          aria-invalid={Boolean(cityError || legacyCity)}
          className={`${selectClassName} cursor-pointer disabled:cursor-not-allowed disabled:opacity-60`}
        >
          <option value="" disabled>
            {cityPlaceholder}
          </option>
          {preserveCurrentCity && (
            <option value={LEGACY_CITY_VALUE}>{city}</option>
          )}
          {cities.map((option) => (
            <option key={option.id} value={option.id}>
              {cityOptionLabel(option, cities)}
            </option>
          ))}
        </select>
      </div>

      {(provinceError || cityError) && (
        <div
          role="alert"
          className="flex items-center justify-between gap-3 text-xs text-red-500 sm:col-span-2"
        >
          <span>{provinceError || cityError}</span>
          <button
            type="button"
            onClick={provinceError ? retryProvinces : retryCities}
            className="shrink-0 font-medium text-brand-600 hover:underline"
          >
            تلاش دوباره
          </button>
        </div>
      )}

      {(legacyProvince || legacyCity) && (
        <p
          role="status"
          className="text-xs leading-5 text-amber-600 sm:col-span-2"
        >
          {legacyProvince
            ? `استان ذخیره‌شده «${province}» در فهرست فعلی نیست؛ لطفاً استان و شهر را دوباره انتخاب کنید.`
            : ambiguousLegacyCity
              ? `برای شهر ذخیره‌شده «${city}» چند گزینه هم‌نام وجود دارد؛ برای ثبت کد رسمی، شهرستان را انتخاب کنید.`
              : `شهر ذخیره‌شده «${city}» در فهرست فعلی نیست؛ لطفاً شهر را دوباره انتخاب کنید.`}
        </p>
      )}
    </div>
  );
}
