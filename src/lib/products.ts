export type Product = {
  id: number;
  title: string;
  category: string;
  price: number;
  oldPrice?: number;
  rating: number;
  ratingCount: number;
  emoji: string;
  badge?: string;
};

export const categories = [
  { slug: "garden-tools", title: "ابزار باغبانی", emoji: "🌿" },
  { slug: "sprayers", title: "سمپاش‌ها", emoji: "💧" },
  { slug: "power-tools", title: "ابزار موتوری", emoji: "🪚" },
  { slug: "irrigation", title: "آبیاری", emoji: "🚿" },
  { slug: "seeds", title: "بذر و نهال", emoji: "🌱" },
  { slug: "machinery", title: "ماشین‌آلات", emoji: "🚜" },
  { slug: "safety", title: "ایمنی و حفاظت", emoji: "🧤" },
  { slug: "fertilizer", title: "کود و سم", emoji: "🧪" },
];

export const products: Product[] = [
  {
    id: 1,
    title: "اره موتوری حرفه‌ای ۵۲ سی‌سی با تیغه ۵۰ سانتی",
    category: "ابزار موتوری",
    price: 4850000,
    oldPrice: 5600000,
    rating: 4.6,
    ratingCount: 213,
    emoji: "🪚",
    badge: "پرفروش",
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
