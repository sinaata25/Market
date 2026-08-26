"use client";

import { useEffect } from "react";

/**
 * ارتفاع واقعی هدر چسبان را در متغیر CSS `--header-h` می‌نویسد.
 *
 * هدر در breakpointهای مختلف ارتفاع متفاوتی دارد (نوار جستجو روی موبایل به سطر
 * دوم می‌رود) و با زوم مرورگر یا تغییر اندازه‌ی فونت هم عوض می‌شود. به‌جای عددهای
 * ثابت، همه‌ی offsetهای چسبان و پنل‌های کشویی از این متغیر استفاده می‌کنند تا
 * هیچ‌وقت زیر هدر پنهان نشوند.
 */
export default function HeaderHeightProbe() {
  useEffect(() => {
    const header = document.querySelector("header");
    if (!header) return;

    const root = document.documentElement;
    const apply = () => {
      const height = header.getBoundingClientRect().height;
      if (height > 0) root.style.setProperty("--header-h", `${Math.round(height)}px`);
    };

    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(header);
    // تغییر جهت/چرخش دستگاه همیشه ResizeObserver را تریگر نمی‌کند
    window.addEventListener("orientationchange", apply);

    return () => {
      observer.disconnect();
      window.removeEventListener("orientationchange", apply);
      root.style.removeProperty("--header-h");
    };
  }, []);

  return null;
}
