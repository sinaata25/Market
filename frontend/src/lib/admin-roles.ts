// نقش‌های پنل مدیریت — تنها مرجعِ تصمیم‌گیریِ نمایشی در فرانت
//
// این ماژول فقط ناوبری و نمایش را کنترل می‌کند؛ مرجع نهایی مجوزها بک‌اند است
// (`accounts/permissions.py`). هر مسیری که اینجا اجازه داده شود، باز هم در
// سمت سرور بررسی می‌شود.
//
// سلسله‌مراتب: سوپریوزر (توسعه‌دهنده) ⊃ مدیر اجرایی (کسب‌وکار)؛
// مدیر سئو ناحیه‌ی جداگانه‌ای دارد که هیچ‌کدام از آن دو به آن دسترسی ندارند.

export type Me = {
  id: number;
  phone: string;
  name: string | null;
  isStaff?: boolean;
  isSuperuser?: boolean;
  isManagerAdmin?: boolean;
  isSeoManager?: boolean;
};

export const SEO_ROOT = "/admin/seo";
export const SHOP_ROOT = "/admin";

// ناحیه‌ی توسعه‌دهنده/سیستمی — فقط سوپریوزر
export const DEVELOPER_ROUTES = ["/admin/managers", "/admin/seo-admins"];

/** «مدیر سئو»: فقط پنل سئو — staff و سوپریوزر عمداً مستثنا هستند */
export function isSeoAdmin(me: Me | null): boolean {
  return Boolean(me?.isSeoManager && !me.isStaff && !me.isSuperuser);
}

/** «مدیر اجرایی»: کل داشبورد کسب‌وکار، بدون ناحیه‌ی سیستمی */
export function isManagerAdmin(me: Me | null): boolean {
  return Boolean(
    me?.isManagerAdmin && me.isStaff && !me.isSuperuser && !me.isSeoManager
  );
}

/** دسترسی داشبورد فروشگاه — سوپریوزر، مدیر اجرایی و کارمند */
export function isShopAdmin(me: Me | null): boolean {
  return Boolean(me?.isStaff && !me.isSeoManager);
}

/** نقش توسعه‌دهنده/سیستمی — تنها نقشی که نقش ممتاز می‌سازد */
export function isDeveloperAdmin(me: Me | null): boolean {
  return Boolean(me?.isSuperuser && !me.isSeoManager);
}

/** آیا مسیر، داخل ناحیه‌ی سئوست؟ («/admin/seo-admins» عمداً بیرون است) */
export function isSeoRoute(pathname: string): boolean {
  return pathname === SEO_ROOT || pathname.startsWith(`${SEO_ROOT}/`);
}

/** آیا مسیر، ناحیه‌ی توسعه‌دهنده است؟ */
export function isDeveloperRoute(pathname: string): boolean {
  return DEVELOPER_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

/**
 * مقصد مجاز کاربر برای یک مسیر؛ `null` یعنی همین‌جا بماند.
 * مدیر سئو بیرون از /admin/seo کاری ندارد، و ناحیه‌ی سیستمی فقط مال سوپریوزر است.
 */
export function adminRedirectFor(
  me: Me | null,
  pathname: string
): string | null {
  if (!me) return null;
  const seoRoute = isSeoRoute(pathname);
  if (isSeoAdmin(me)) return seoRoute ? null : SEO_ROOT;
  if (seoRoute) return SHOP_ROOT;
  if (isDeveloperRoute(pathname) && !isDeveloperAdmin(me)) return SHOP_ROOT;
  return null;
}
