// تبدیل ارقام فارسی/عربی به انگلیسی برای اعتبارسنجی و پردازش
export function toEnglishDigits(input: string): string {
  const persian = "۰۱۲۳۴۵۶۷۸۹";
  const arabic = "٠١٢٣٤٥٦٧٨٩";
  return input.replace(/[۰-۹٠-٩]/g, (ch) => {
    const p = persian.indexOf(ch);
    if (p > -1) return String(p);
    const a = arabic.indexOf(ch);
    if (a > -1) return String(a);
    return ch;
  });
}

export function normalizeIranMobile(value: string): string {
  let phone = toEnglishDigits(value)
    .replace(/\s/g, "")
    .replace(/[-()]/g, "");
  if (phone.startsWith("+98")) phone = `0${phone.slice(3)}`;
  else if (phone.startsWith("0098")) phone = `0${phone.slice(4)}`;
  else if (phone.startsWith("98") && phone.length === 12) {
    phone = `0${phone.slice(2)}`;
  }
  return phone;
}

// اعتبارسنجی شماره موبایل ایران: ۱۱ رقم و شروع با ۰۹
export function isValidIranMobile(value: string): boolean {
  return /^09\d{9}$/.test(normalizeIranMobile(value));
}

// فقط مسیر نسبی همان origin را برای redirect پس از ورود می‌پذیرد.
export function safeNextPath(value: string | null | undefined): string {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    /[\r\n]/.test(value)
  ) {
    return "/";
  }

  try {
    const base = "https://market.local";
    const url = new URL(value, base);
    if (url.origin !== base) return "/";
    if (url.pathname.replace(/\/+$/, "") === "/login") return "/";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return "/";
  }
}
