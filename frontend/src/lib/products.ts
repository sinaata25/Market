export type ProductSpecification = {
  keyId: number;
  name: string;
  slug: string;
  value: string;
  position: number;
};

export type Product = {
  id: number;
  title: string;
  titleEn?: string;
  category: string;
  categorySlug?: string;
  categories?: { slug: string; title: string }[];
  categorySlugs?: string[];
  brand?: Brand | null;
  price: number;
  oldPrice?: number;
  rating: number;
  ratingCount: number;
  image?: string | null;
  images?: string[];
  badge?: string;
  colors?: { name: string; hex: string }[];
  features?: string[];
  // Only product-detail responses include the normalized specification rows.
  specifications?: ProductSpecification[];
  description?: string;
  warranty?: string;
  // دو خط اطلاع‌رسانی جعبه‌ی خرید — اختیاری و بدون پیش‌فرض
  shippingNote?: string;
  returnNote?: string;
  stock?: number;
  isActive?: boolean;
  // انتخاب دستی مدیر برای بخش «پرفروش‌ترین‌ها» — مستقل از rating/ratingCount واقعی
  isBestSeller?: boolean;
  bestSellerPosition?: number;
  // انتخاب دستی مدیر برای بخش «شگفت‌انگیزها» — مستقل از داشتن تخفیف
  isIncredible?: boolean;
  incrediblePosition?: number;
};

export type Brand = {
  name: string;
  slug: string;
  description?: string | null;
  logo?: string | null;
  website?: string | null;
  isActive?: boolean;
  productCount?: number;
  id?: number;
};

export type Category = {
  slug: string;
  title: string;
  icon: string | null;
  sub: { slug: string; title: string }[];
  isTopLevel?: boolean;
  isActive?: boolean;
  effectiveIsActive?: boolean;
};

// ناوبری تا زمان دریافت داده‌ی زنده از API با این فهرست بدون آیکن قابل استفاده می‌ماند.
export const categories: Category[] = [
  {
    slug: "garden-tools",
    title: "ابزار باغبانی",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "sprayers",
    title: "سمپاش‌ها",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "power-tools",
    title: "ابزار موتوری",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "irrigation",
    title: "آبیاری",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "seeds",
    title: "بذر و نهال",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "machinery",
    title: "ماشین‌آلات",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "safety",
    title: "ایمنی و حفاظت",
    icon: null,
    sub: [],
    isTopLevel: true,
  },
  {
    slug: "fertilizer",
    title: "کود و سم",
    icon: null,
    sub: [],
    isTopLevel: true,
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
    specifications: [
      {
        keyId: 1,
        name: "حجم موتور",
        slug: "حجم-موتور",
        value: "۵۲ سی‌سی",
        position: 0,
      },
      {
        keyId: 2,
        name: "طول تیغه",
        slug: "طول-تیغه",
        value: "۵۰ سانتی‌متر",
        position: 1,
      },
      {
        keyId: 3,
        name: "نوع موتور",
        slug: "نوع-موتور",
        value: "بنزینی دو زمانه",
        position: 2,
      },
      {
        keyId: 4,
        name: "ظرفیت مخزن سوخت",
        slug: "ظرفیت-مخزن-سوخت",
        value: "۵۵۰ میلی‌لیتر",
        position: 3,
      },
      {
        keyId: 5,
        name: "وزن",
        slug: "وزن",
        value: "۵.۸ کیلوگرم",
        position: 4,
      },
      {
        keyId: 6,
        name: "کشور سازنده",
        slug: "کشور-سازنده",
        value: "آلمان",
        position: 5,
      },
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
    badge: "تخفیف ویژه",
  },
  {
    id: 3,
    title: "بیل باغبانی استیل ضدزنگ دسته چوبی",
    category: "ابزار باغبانی",
    price: 420000,
    rating: 4.8,
    ratingCount: 89,
  },
  {
    id: 4,
    title: "شیلنگ آبیاری تقویت‌شده ۲۰ متری ضد پیچش",
    category: "آبیاری",
    price: 690000,
    oldPrice: 820000,
    rating: 4.3,
    ratingCount: 64,
  },
  {
    id: 5,
    title: "قیچی باغبانی شاخه‌زنی تیغه فولادی ژاپنی",
    category: "ابزار باغبانی",
    price: 350000,
    rating: 4.7,
    ratingCount: 142,
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
  },
  {
    id: 7,
    title: "دستکش کار ضد برش مخصوص باغبانی (جفت)",
    category: "ایمنی و حفاظت",
    price: 95000,
    rating: 4.2,
    ratingCount: 47,
  },
  {
    id: 8,
    title: "کود مایع رشد گیاهان ۱ لیتری غلیظ",
    category: "کود و سم",
    price: 145000,
    oldPrice: 175000,
    rating: 4.6,
    ratingCount: 98,
    badge: "تخفیف ویژه",
  },
];

/** تعداد کالاهای هر صفحه‌ی بخش «همه محصولات» صفحه اصلی */
export const HOME_PRODUCTS_PER_PAGE = 6;

/** صفحه‌ی کامل فهرست محصولات — مقصد دکمه‌های «مشاهده همه» */
export const ALL_PRODUCTS_PATH = "/products";

export function formatPrice(value: number) {
  return value.toLocaleString("fa-IR");
}

/** آیا محصول تخفیف واقعی دارد؟ (قیمت قبل باید بیشتر از قیمت فعلی باشد) */
export function hasDiscount(product: Pick<Product, "price" | "oldPrice">) {
  return typeof product.oldPrice === "number" && product.oldPrice > product.price;
}

/**
 * درصد تخفیف — تنها جای محاسبه‌ی آن در فرانت.
 * بک‌اند فقط price و oldPrice می‌دهد و درصد را محاسبه نمی‌کند.
 */
export function discountPercent(
  product: Pick<Product, "price" | "oldPrice">
): number {
  if (!hasDiscount(product)) return 0;
  return Math.round((1 - product.price / product.oldPrice!) * 100);
}

// توجه: کوئری‌های محصولات از دیتابیس در src/lib/catalog.ts هستند.
// آرایه‌ی محصولات بالا فقط به‌عنوان داده‌ی اولیه (seed) دیتابیس استفاده می‌شود.
