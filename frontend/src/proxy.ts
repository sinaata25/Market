import { NextResponse, type NextRequest } from "next/server";

// اعمال ریدایرکت‌های ثبت‌شده در پنل سئو (301/302)
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/seo/resolve?path=${encodeURIComponent(path)}`,
      { signal: AbortSignal.timeout(1500) }
    );
    const json = await res.json();
    const redirect = json?.data?.redirect;
    if (redirect?.to) {
      const url = new URL(redirect.to, request.url);
      return NextResponse.redirect(url, redirect.status === 302 ? 302 : 301);
    }
  } catch {
    // بک‌اند در دسترس نیست — بدون ریدایرکت ادامه بده
  }
  return NextResponse.next();
}

export const config = {
  // فقط صفحات سایت؛ نه API، مدیا، فایل‌های استاتیک و پنل ادمین
  matcher: [
    "/((?!api|media|_next|admin|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
