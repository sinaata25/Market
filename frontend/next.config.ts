import type { NextConfig } from "next";
import path from "path";

// آدرس بک‌اند جنگو — در استقرار واقعی از متغیر محیطی خوانده می‌شود
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // ریشه‌ی workspace را به همین پوشه محدود می‌کند تا هشدار چند lockfile رفع شود
  turbopack: {
    root: path.join(__dirname),
  },
  // همه‌ی درخواست‌های /api/* به جنگو پروکسی می‌شوند؛
  // به این ترتیب کوکی سشن و CSRF همان‌origin می‌مانند
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
      // فایل‌های رسانه‌ای محصولات و دسته‌بندی‌ها هم از جنگو سرو می‌شوند
      {
        source: "/media/:path*",
        destination: `${BACKEND_URL}/media/:path*`,
      },
      // فایل‌های سئو از جنگو (قابل مدیریت از پنل سئو)
      {
        source: "/robots.txt",
        destination: `${BACKEND_URL}/robots.txt`,
      },
      {
        source: "/sitemap.xml",
        destination: `${BACKEND_URL}/sitemap.xml`,
      },
    ];
  },
};

export default nextConfig;
