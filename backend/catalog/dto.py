"""تبدیل مدل‌ها به همان ساختاری که فرانت Next.js انتظار دارد (camelCase)"""

from .models import Brand, Category, Product

DEFAULT_FEATURES = [
    "کیفیت ساخت بالا و بادوام",
    "مناسب استفاده حرفه‌ای و خانگی",
    "ضمانت اصالت کالا",
]


def category_summary(category: Category) -> dict:
    return {
        "slug": category.slug,
        "title": category.title,
    }


def brand_dto(brand: Brand) -> dict:
    return {
        "name": brand.name,
        "slug": brand.slug,
        "description": brand.description or None,
        "logo": brand.logo.url if brand.logo else None,
        "website": brand.website or None,
        "isActive": brand.is_active,
    }


def category_dto(
    category: Category, *, visible_ids: set[int] | None = None
) -> dict:
    children = list(category.children.all())
    if visible_ids is not None:
        children = [child for child in children if child.pk in visible_ids]
    return {
        "slug": category.slug,
        "title": category.title,
        "icon": category.icon.url if category.icon else None,
        "sub": [category_summary(child) for child in children],
        "isTopLevel": not category.parents.exists(),
    }


def product_dto(product: Product, *, include_specifications: bool = False) -> dict:
    assigned_categories = list(product.categories.all())
    categories = [product.category] + [
        category
        for category in assigned_categories
        if category.pk != product.category_id
    ]
    category = categories[0]
    # آدرس‌های نسبی /media/… — فرانت آن‌ها را به جنگو پروکسی می‌کند
    images = [img.image.url for img in product.images.all()]
    data = {
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
        "brand": brand_dto(product.brand) if product.brand_id else None,
        "price": product.price,
        "oldPrice": product.old_price,
        "rating": product.rating,
        "ratingCount": product.rating_count,
        "badge": product.badge or None,
        "colors": product.colors,
        "features": product.features or DEFAULT_FEATURES,
        "description": product.description
        or (
            f"{product.title} با کیفیت مناسب و قیمت رقابتی، یکی از محصولات "
            f"پرطرفدار دسته {category.title} است که با ضمانت اصالت کالا عرضه می‌شود."
        ),
        "warranty": product.warranty or "۱۲ ماه ضمانت فروشگاه",
        "stock": product.stock,
        "isActive": product.is_active,
    }
    if include_specifications:
        data["specifications"] = [
            {
                "keyId": item.key_id,
                "name": item.key.name,
                "slug": item.key.slug,
                "value": item.value,
                "position": item.position,
            }
            for item in product.specifications.all()
        ]
    return data
