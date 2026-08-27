// نقش‌های پنل مدیریت — تنها مرجعِ تصمیم‌گیریِ نمایشی در فرانت
//
// این ماژول فقط ناوبری و نمایش را کنترل می‌کند؛ مرجع نهایی مجوزها بک‌اند است
// (`accounts/roles.py`). هر مسیری که اینجا اجازه داده شود، باز هم در سمت
// سرور بررسی می‌شود و هر مسیری که اینجا پنهان شود، تایپ‌کردن دستی‌اش هم به
// جایی نمی‌رسد. پنهان‌کردن در فرانت فقط برای تجربه‌ی کاربری است.
//
// سلسله‌مراتب:
//
//     مدیر سیستم
//         ├── مدیر اجرایی ── مدیر عادی ── مشتری
//         └── مدیر سئو            (شاخه‌ی تخصصی و جدا)
//
// مدیر اجرایی فقط وقتی وارد شاخه‌ی سئو می‌شود که سوپریوزر صراحتاً اجازه داده
// باشد؛ این را بک‌اند در `canAccessSeo` پاسخ `/api/auth/me` حساب می‌کند.

export type Role =
  | "superuser"
  | "manager_admin"
  | "regular_admin"
  | "seo_admin"
  | "customer";

export type Me = {
  id: number;
  phone: string;
  name: string | null;
  /** نقشِ استنتاج‌شده از بک‌اند — مرجع اصلی */
  role?: Role;
  /** «به پنل سئو راه دارد» (نه فلگ خام) — بک‌اند حسابش می‌کند */
  canAccessSeo?: boolean;
  // فلگ‌های خام؛ فقط برای سازگاری با پاسخ‌های قدیمی نگه داشته شده‌اند
  isStaff?: boolean;
  isSuperuser?: boolean;
  isManagerAdmin?: boolean;
  isSeoManager?: boolean;
};

export const ROLE_LABELS: Record<Role, string> = {
  superuser: "مدیر سیستم",
  manager_admin: "مدیر اجرایی",
  regular_admin: "مدیر عادی",
  seo_admin: "مدیر سئو",
  customer: "مشتری",
};

export const ROLE_BADGES: Record<Role, string> = {
  superuser: "bg-rose-50 text-rose-600",
  manager_admin: "bg-violet-50 text-violet-600",
  regular_admin: "bg-blue-50 text-blue-600",
  seo_admin: "bg-amber-50 text-amber-600",
  customer: "bg-slate-100 text-slate-500",
};

export const SEO_ROOT = "/admin/seo";
export const SHOP_ROOT = "/admin";

/** ناحیه‌ی سطح‌سیستم — فقط مدیر سیستم */
export const DEVELOPER_ROUTES = ["/admin/managers"];

/** مدیریت حساب‌های مدیر سئو — مدیر سیستم یا مدیر اجرایی دارای دسترسی سئو */
export const SEO_ADMIN_ROUTES = ["/admin/seo-admins"];

/** نقش کاربر؛ اگر بک‌اند `role` نداد، از فلگ‌های قدیمی استنتاج می‌شود */
export function roleOf(me: Me | null): Role | null {
  if (!me) return null;
  if (me.role) return me.role;
  if (me.isSuperuser) return "superuser";
  if (me.isSeoManager) return "seo_admin";
  if (me.isManagerAdmin && me.isStaff) return "manager_admin";
  if (me.isStaff) return "regular_admin";
  return "customer";
}

/** حسابِ «مدیر سئو» — کل کارش شاخه‌ی سئوست */
export function isSeoAdmin(me: Me | null): boolean {
  return roleOf(me) === "seo_admin";
}

/** «مدیر اجرایی» — کل داشبورد کسب‌وکار، بدون ناحیه‌ی سطح‌سیستم */
export function isManagerAdmin(me: Me | null): boolean {
  return roleOf(me) === "manager_admin";
}

/** «مدیر عادی» — کارهای عملیاتی، با مدیریت کاربرِ محدود به مشتری‌ها */
export function isRegularAdmin(me: Me | null): boolean {
  return roleOf(me) === "regular_admin";
}

/** در ورودی داشبورد فروشگاه */
export function isShopAdmin(me: Me | null): boolean {
  const role = roleOf(me);
  return (
    role === "superuser" || role === "manager_admin" || role === "regular_admin"
  );
}

/** مدیر سیستم — بالاترین سطح */
export function isDeveloperAdmin(me: Me | null): boolean {
  return roleOf(me) === "superuser";
}

/** دسترسی به پنل سئو — بک‌اند تصمیم گرفته، اینجا فقط خوانده می‌شود */
export function canAccessSeo(me: Me | null): boolean {
  if (!me) return false;
  if (me.canAccessSeo !== undefined) return me.canAccessSeo;
  // سازگاری با پاسخ قدیمی که این فیلد را نداشت
  const role = roleOf(me);
  return role === "superuser" || role === "seo_admin";
}

/** مدیریت حساب‌های مدیر سئو */
export function canManageSeoAdmins(me: Me | null): boolean {
  return (
    isDeveloperAdmin(me) || (isManagerAdmin(me) && canAccessSeo(me))
  );
}

/** مدیریت حساب‌های مدیر اجرایی و دادن دسترسی سئو — فقط مدیر سیستم */
export function canManageManagers(me: Me | null): boolean {
  return isDeveloperAdmin(me);
}

function matches(pathname: string, routes: string[]): boolean {
  return routes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

/** آیا مسیر داخل شاخه‌ی سئوست؟ («/admin/seo-admins» عمداً بیرون است) */
export function isSeoRoute(pathname: string): boolean {
  return pathname === SEO_ROOT || pathname.startsWith(`${SEO_ROOT}/`);
}

/** آیا مسیر، ناحیه‌ی سطح‌سیستم است؟ */
export function isDeveloperRoute(pathname: string): boolean {
  return matches(pathname, DEVELOPER_ROUTES);
}

/** آیا مسیر، مدیریت حساب‌های مدیر سئوست؟ */
export function isSeoAdminRoute(pathname: string): boolean {
  return matches(pathname, SEO_ADMIN_ROUTES);
}

/** خانه‌ی هر نقش */
export function homeFor(me: Me | null): string {
  return isSeoAdmin(me) ? SEO_ROOT : SHOP_ROOT;
}

/**
 * مقصد مجاز کاربر برای یک مسیر؛ `null` یعنی همین‌جا بماند.
 *
 * مدیر سئو بیرون از /admin/seo کاری ندارد، شاخه‌ی سئو دسترسی صریح می‌خواهد،
 * و ناحیه‌ی سطح‌سیستم فقط مال مدیر سیستم است.
 */
export function adminRedirectFor(
  me: Me | null,
  pathname: string
): string | null {
  if (!me) return null;

  if (isSeoRoute(pathname)) {
    return canAccessSeo(me) ? null : homeFor(me);
  }
  // بیرون از شاخه‌ی سئو، مدیر سئو هیچ‌جا نمی‌رود
  if (isSeoAdmin(me)) return SEO_ROOT;

  if (isDeveloperRoute(pathname) && !canManageManagers(me)) return SHOP_ROOT;
  if (isSeoAdminRoute(pathname) && !canManageSeoAdmins(me)) return SHOP_ROOT;
  return null;
}
