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
        "icon": category.icon.url if category.icon else None,
        "sub": category.sub or [],
    }


def product_dto(product: Product) -> dict:
    assigned_categories = list(product.categories.all())
    categories = [product.category] + [
        category
        for category in assigned_categories
        if category.pk != product.category_id
    ]
    category = categories[0]
    # آدرس‌های نسبی /media/… — فرانت آن‌ها را به جنگو پروکسی می‌کند
    images = [img.image.url for img in product.images.all()]
    return {
        "image": images[0] if images else None,
        "images": images,
        "id": product.id,
        "title": product.title,
        "titleEn": product.title_en or None,
        "category": category.title,
        "categorySlug": category.slug,
        "categories": [
            {"slug": item.slug, "title": item.title} for item in categories
        ],
        "categorySlugs": [item.slug for item in categories],
        "price": product.price,
        "oldPrice": product.old_price,
        "rating": product.rating,
        "ratingCount": product.rating_count,
        "badge": product.badge or None,
        "colors": product.colors,
        "features": product.features or DEFAULT_FEATURES,
        "specs": product.specs
        or [
            {
                "label": "دسته‌بندی",
                "value": "، ".join(item.title for item in categories),
            },
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
