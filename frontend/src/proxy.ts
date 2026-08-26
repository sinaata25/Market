import { NextResponse, type NextRequest } from "next/server";

import { adminRedirectFor, type Me } from "@/lib/admin-roles";

// اعمال ریدایرکت‌های ثبت‌شده در پنل سئو (301/302)
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** نقش کاربر جاری را از بک‌اند می‌پرسد؛ کوکی سشن عیناً فوروارد می‌شود */
async function fetchMe(request: NextRequest): Promise<Me | null> {
  const cookie = request.headers.get("cookie");
  if (!cookie) return null;
  const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
    headers: { cookie },
    signal: AbortSignal.timeout(1500),
  });
  if (!res.ok) return null;
  const json = await res.json();
  return (json?.data?.user as Me | undefined) ?? null;
}

/**
 * نگهبان ناوبریِ پنل مدیریت: مدیر سئو را از بخش‌های فروشگاهی و بقیه را از
 * ناحیه‌ی سئو بیرون می‌برد تا تایپ‌کردن دستی آدرس هم بی‌اثر باشد.
 *
 * این فقط لایه‌ی ناوبری است — طبق راهنمای Next، proxy جای احراز مجوز نیست؛
 * هر API پشت آن مستقلاً در جنگو مجوز را بررسی می‌کند.
 */
async function adminRouteGuard(request: NextRequest) {
  let me: Me | null;
  try {
    me = await fetchMe(request);
  } catch {
    // بک‌اند در دسترس نیست — لایه‌های بعدی (layout و خودِ API) تصمیم می‌گیرند
    return null;
  }

  const target = adminRedirectFor(me, request.nextUrl.pathname);
  if (!target) return null;
  return NextResponse.redirect(new URL(target, request.url));
}

export async function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;

  if (path === "/admin" || path.startsWith("/admin/")) {
    return (await adminRouteGuard(request)) ?? NextResponse.next();
  }

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
  // پنل ادمین برای نگهبانِ نقش‌ها؛ بقیه‌ی صفحات سایت برای ریدایرکت‌های سئو
  matcher: [
    "/admin/:path*",
    "/((?!api|media|_next|admin|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
