export type Product = {
  id: number;
  title: string;
  titleEn?: string;
  category: string;
  categorySlug?: string;
  price: number;
  oldPrice?: number;
  rating: number;
  ratingCount: number;
  emoji: string;
  badge?: string;
  colors?: { name: string; hex: string }[];
  features?: string[];
  specs?: { label: string; value: string }[];
  description?: string;
  warranty?: string;
  stock?: number;
};

export type Category = {
  slug: string;
  title: string;
  emoji: string;
  sub: string[];
};

export const categories: Category[] = [
  {
    slug: "garden-tools",
    title: "ابزار باغبانی",
    emoji: "🌿",
    sub: ["بیل و کلنگ", "قیچی باغبانی", "شن‌کش", "اره شاخه‌زنی", "ماله و کج‌بیل"],
  },
  {
    slug: "sprayers",
    title: "سمپاش‌ها",
    emoji: "💧",
    sub: ["سمپاش پشتی", "سمپاش شارژی", "سمپاش موتوری", "سمپاش دستی", "نازل و لوازم جانبی"],
  },
  {
    slug: "power-tools",
    title: "ابزار موتوری",
    emoji: "🪚",
    sub: ["اره موتوری", "علف‌زن", "موتور برق", "دروگر", "تیلر و کولتیواتور"],
  },
  {
    slug: "irrigation",
    title: "آبیاری",
    emoji: "🚿",
    sub: ["شیلنگ آبیاری", "آبیاری قطره‌ای", "پمپ آب", "اتصالات", "تایمر آبیاری"],
  },
  {
    slug: "seeds",
    title: "بذر و نهال",
    emoji: "🌱",
    sub: ["بذر سبزیجات", "بذر صیفی", "نهال میوه", "پیاز گل", "خاک و بستر کشت"],
  },
  {
    slug: "machinery",
    title: "ماشین‌آلات",
    emoji: "🚜",
    sub: ["تراکتور", "ادوات خاک‌ورزی", "کمباین", "نشاکار", "یدکی ماشین‌آلات"],
  },
  {
    slug: "safety",
    title: "ایمنی و حفاظت",
    emoji: "🧤",
    sub: ["دستکش کار", "ماسک و فیلتر", "عینک ایمنی", "چکمه و کفش کار", "لباس کار"],
  },
  {
    slug: "fertilizer",
    title: "کود و سم",
    emoji: "🧪",
    sub: ["کود شیمیایی", "کود آلی", "سم دفع آفات", "علف‌کش", "محرک رشد"],
  },
];

export const products: Product[] = [
  {
    id: 1,
    title: "اره موتوری حرفه‌ای ۵۲ سی‌سی با تیغه ۵۰ سانتی",
    titleEn: "Professional Chainsaw 52cc 50cm",
    category: "ابزار موتوری",
    price: 4850000,
    oldPrice: 5600000,
    rating: 4.6,
    ratingCount: 213,
    emoji: "🪚",
    badge: "پرفروش",
    colors: [
      { name: "نارنجی", hex: "#ea580c" },
      { name: "خاکستری", hex: "#475569" },
    ],
    features: [
      "موتور دو زمانه پرقدرت ۵۲ سی‌سی",
      "تیغه ۵۰ سانتی‌متری مناسب برش درختان قطور",
      "سیستم استارت آسان و کم‌مصرف",
      "دسته ضد لرزش برای کاهش خستگی",
    ],
    specs: [
      { label: "حجم موتور", value: "۵۲ سی‌سی" },
      { label: "طول تیغه", value: "۵۰ سانتی‌متر" },
      { label: "نوع موتور", value: "بنزینی دو زمانه" },
      { label: "ظرفیت مخزن سوخت", value: "۵۵۰ میلی‌لیتر" },
      { label: "وزن", value: "۵.۸ کیلوگرم" },
      { label: "کشور سازنده", value: "آلمان" },
    ],
    description:
      "اره موتوری حرفه‌ای با موتور پرقدرت ۵۲ سی‌سی، مناسب برای هرس و برش درختان باغ و کارهای سنگین کشاورزی. طراحی ارگونومیک و سیستم ضد لرزش، استفاده طولانی‌مدت را راحت‌تر می‌کند.",
    warranty: "۱۸ ماه گارانتی شرکتی",
  },
  {
    id: 2,
    title: "سمپاش پشتی شارژی ۱۶ لیتری با باتری لیتیومی",
    category: "سمپاش‌ها",
    price: 1980000,
    oldPrice: 2350000,
    rating: 4.4,
    ratingCount: 156,
    emoji: "💧",
    badge: "تخفیف ویژه",
  },
  {
    id: 3,
    title: "بیل باغبانی استیل ضدزنگ دسته چوبی",
    category: "ابزار باغبانی",
    price: 420000,
    rating: 4.8,
    ratingCount: 89,
    emoji: "🌿",
  },
  {
    id: 4,
    title: "شیلنگ آبیاری تقویت‌شده ۲۰ متری ضد پیچش",
    category: "آبیاری",
    price: 690000,
    oldPrice: 820000,
    rating: 4.3,
    ratingCount: 64,
    emoji: "🚿",
  },
  {
    id: 5,
    title: "قیچی باغبانی شاخه‌زنی تیغه فولادی ژاپنی",
    category: "ابزار باغبانی",
    price: 350000,
    rating: 4.7,
    ratingCount: 142,
    emoji: "✂️",
    badge: "پرفروش",
  },
  {
    id: 6,
    title: "ست بذر سبزیجات ارگانیک ۱۲ عددی",
    category: "بذر و نهال",
    price: 185000,
    oldPrice: 240000,
    rating: 4.5,
    ratingCount: 311,
    emoji: "🌱",
  },
  {
    id: 7,
    title: "دستکش کار ضد برش مخصوص باغبانی (جفت)",
    category: "ایمنی و حفاظت",
    price: 95000,
    rating: 4.2,
    ratingCount: 47,
    emoji: "🧤",
  },
  {
    id: 8,
    title: "کود مایع رشد گیاهان ۱ لیتری غلیظ",
    category: "کود و سم",
    price: 145000,
    oldPrice: 175000,
    rating: 4.6,
    ratingCount: 98,
    emoji: "🧪",
    badge: "تخفیف ویژه",
  },
];

export function formatPrice(value: number) {
  return value.toLocaleString("fa-IR");
}

// توجه: کوئری‌های محصولات از دیتابیس در src/lib/catalog.ts هستند.
// آرایه‌های بالا فقط به‌عنوان داده‌ی اولیه (seed) دیتابیس استفاده می‌شوند.
