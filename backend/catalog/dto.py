"""تبدیل مدل‌ها به همان ساختاری که فرانت Next.js انتظار دارد (camelCase)"""

from .models import Category, Product

DEFAULT_FEATURES = [
    "کیفیت ساخت بالا و بادوام",
    "مناسب استفاده حرفه‌ای و خانگی",
    "ضمانت اصالت کالا",
]


def category_dto(category: Category) -> dict:
    return {
        "slug": category.slug,
        "title": category.title,
        "emoji": category.emoji,
        "sub": category.sub or [],
    }


def product_dto(product: Product) -> dict:
    category = product.category
    return {
        "id": product.id,
        "title": product.title,
        "titleEn": product.title_en or None,
        "category": category.title,
        "categorySlug": category.slug,
        "price": product.price,
        "oldPrice": product.old_price,
        "rating": product.rating,
        "ratingCount": product.rating_count,
        "emoji": product.emoji,
        "badge": product.badge or None,
        "colors": product.colors,
        "features": product.features or DEFAULT_FEATURES,
        "specs": product.specs
        or [
            {"label": "دسته‌بندی", "value": category.title},
            {"label": "وضعیت کالا", "value": "نو و اصل"},
            {"label": "ارسال", "value": "از انبار فروشگاه"},
        ],
        "description": product.description
        or (
            f"{product.title} با کیفیت مناسب و قیمت رقابتی، یکی از محصولات "
            f"پرطرفدار دسته {category.title} است که با ضمانت اصالت کالا عرضه می‌شود."
        ),
        "warranty": product.warranty or "۱۲ ماه ضمانت فروشگاه",
        "stock": product.stock,
    }
