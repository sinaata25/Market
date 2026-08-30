"use client";

import { useEffect, useRef } from "react";
import type { Map as LeafletMap, Marker } from "leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/**
 * تنها جایی از پروژه که به کتابخانه‌ی نقشه وابسته است.
 *
 * Leaflet + کاشی‌های OpenStreetMap انتخاب شده‌اند چون کلید API نمی‌خواهند و
 * هزینه‌ای تولید نمی‌کنند. این کامپوننت فقط با import پویا در داشبورد
 * بارگذاری می‌شود، پس هیچ بایتی از آن به فروشگاه نمی‌رسد. تعویض سرویس‌دهنده
 * یعنی بازنویسی همین فایل، نه گشتن در داشبورد.
 */

// وقتی هنوز موقعیتی انتخاب نشده، نقشه روی مرکز ایران باز می‌شود
const FALLBACK_CENTER: [number, number] = [35.6892, 51.389];
const FALLBACK_ZOOM = 11;

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
  '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// آیکن پیش‌فرض Leaflet به فایل‌های تصویری نسبی وابسته است و با باندلر
// می‌شکند؛ نشانگر برداری درون‌خطی این وابستگی را حذف می‌کند.
const MARKER_ICON = L.divIcon({
  className: "",
  html: `<svg viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">
      <path fill="#467235" stroke="#ffffff" stroke-width="1.2"
        d="M12 1.8c-4 0-7.2 3.2-7.2 7.2 0 5.4 7.2 13.2 7.2 13.2s7.2-7.8 7.2-13.2c0-4-3.2-7.2-7.2-7.2z"/>
      <circle cx="12" cy="9" r="2.6" fill="#ffffff"/>
    </svg>`,
  iconSize: [32, 32],
  iconAnchor: [16, 30],
});

export type LocationMapProps = {
  latitude: number | null;
  longitude: number | null;
  zoom: number;
  onPick: (latitude: number, longitude: number) => void;
  onZoomChange: (zoom: number) => void;
};

export default function LocationMap({
  latitude,
  longitude,
  zoom,
  onPick,
  onZoomChange,
}: LocationMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap | null>(null);
  const marker = useRef<Marker | null>(null);
  // هندلرهای Leaflet یک‌بار وصل می‌شوند؛ آخرین نسخه‌ی callbackها از اینجا
  // خوانده می‌شود تا نقشه با هر رندر دوباره ساخته نشود.
  const handlers = useRef({ onPick, onZoomChange });
  useEffect(() => {
    handlers.current = { onPick, onZoomChange };
  }, [onPick, onZoomChange]);

  useEffect(() => {
    if (!container.current || map.current) return;

    const instance = L.map(container.current, {
      center:
        latitude !== null && longitude !== null
          ? [latitude, longitude]
          : FALLBACK_CENTER,
      zoom: latitude !== null && longitude !== null ? zoom : FALLBACK_ZOOM,
      scrollWheelZoom: false,
    });
    L.tileLayer(TILE_URL, { maxZoom: 19, attribution: TILE_ATTRIBUTION }).addTo(
      instance
    );
    instance.on("click", (event) => {
      handlers.current.onPick(event.latlng.lat, event.latlng.lng);
    });
    instance.on("zoomend", () => {
      handlers.current.onZoomChange(instance.getZoom());
    });
    map.current = instance;

    return () => {
      instance.remove();
      map.current = null;
      marker.current = null;
    };
    // نقشه عمداً فقط یک‌بار ساخته می‌شود؛ همگام‌سازی مقادیر در افکت بعدی است
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // همگام‌سازی نشانگر با مقادیر فرم — چه از کلیک روی نقشه آمده باشند، چه از
  // جست‌وجو، چه از تایپ دستی مختصات
  useEffect(() => {
    const instance = map.current;
    if (!instance) return;

    if (latitude === null || longitude === null) {
      marker.current?.remove();
      marker.current = null;
      return;
    }

    const position: [number, number] = [latitude, longitude];
    if (!marker.current) {
      const pin = L.marker(position, { draggable: true, icon: MARKER_ICON });
      pin.on("dragend", () => {
        const { lat, lng } = pin.getLatLng();
        handlers.current.onPick(lat, lng);
      });
      pin.addTo(instance);
      marker.current = pin;
    } else {
      marker.current.setLatLng(position);
    }

    // فقط وقتی نقطه بیرون از کادر دید است نقشه جابه‌جا می‌شود، تا کشیدن
    // نشانگر با پرش دوباره‌ی نقشه همراه نباشد
    if (!instance.getBounds().contains(position)) {
      instance.setView(position, Math.max(instance.getZoom(), 13));
    }
  }, [latitude, longitude]);

  return (
    <div
      ref={container}
      role="application"
      aria-label="نقشه‌ی انتخاب موقعیت فروشگاه"
      className="h-72 w-full overflow-hidden rounded-xl border border-slate-200 sm:h-80"
    />
  );
}
