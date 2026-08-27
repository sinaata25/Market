const DIGIT_MAP: Record<string, string> = {
  "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
  "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
  "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
  "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
};

export function normalizeSearchText(value: string): string {
  return value
    .normalize("NFKC")
    .replace(/[يى]/gu, "ی")
    .replace(/ك/gu, "ک")
    .replace(/[٠-٩۰-۹]/gu, (digit) => DIGIT_MAP[digit] ?? digit)
    .replace(/[\u00a0\u200c]/gu, " ")
    .replace(/\s+/gu, " ")
    .trim()
    .toLocaleLowerCase("fa-IR");
}

export function searchTextIncludes(value: string, query: string): boolean {
  const normalizedValue = normalizeSearchText(value);
  return normalizeSearchText(query)
    .split(" ")
    .filter(Boolean)
    .every((token) => normalizedValue.includes(token));
}
