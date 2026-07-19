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

// اعتبارسنجی شماره موبایل ایران: ۱۱ رقم و شروع با ۰۹
export function isValidIranMobile(value: string): boolean {
  const normalized = toEnglishDigits(value).replace(/\s/g, "");
  return /^09\d{9}$/.test(normalized);
}
