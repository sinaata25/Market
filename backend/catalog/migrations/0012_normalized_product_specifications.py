import re
import unicodedata

import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify


ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
SPACE_RE = re.compile(r"\s+")


def normalize_name(value):
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.translate(ARABIC_TO_PERSIAN)
    text = text.replace("\u00a0", " ").replace("\u200c", " ")
    display_name = SPACE_RE.sub(" ", text).strip()
    return display_name, display_name.casefold()


def unique_slug(SpecificationKey, name, db_alias):
    max_length = 120
    base = slugify(name, allow_unicode=True).strip("-") or "specification"
    base = base[:max_length].rstrip("-") or "specification"
    candidate = base
    suffix = 2
    while SpecificationKey.objects.using(db_alias).filter(slug=candidate).exists():
        marker = f"-{suffix}"
        candidate = f"{base[: max_length - len(marker)].rstrip('-')}{marker}"
        suffix += 1
    return candidate


def migrate_legacy_specs(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    SpecificationKey = apps.get_model("catalog", "SpecificationKey")
    ProductSpecification = apps.get_model("catalog", "ProductSpecification")
    db_alias = schema_editor.connection.alias

    products = Product.objects.using(db_alias).exclude(specs__isnull=True)
    for product in products.iterator():
        raw_specs = product.specs
        if not isinstance(raw_specs, list):
            continue
        seen_normalized_names = set()
        rows = []
        for position, raw_spec in enumerate(raw_specs):
            if not isinstance(raw_spec, dict):
                continue
            name, normalized_name = normalize_name(raw_spec.get("label"))
            value = unicodedata.normalize(
                "NFKC", str(raw_spec.get("value") or "")
            ).strip()
            if (
                not name
                or len(name) > 100
                or not value
                or len(value) > 500
                or normalized_name in seen_normalized_names
            ):
                continue
            key = SpecificationKey.objects.using(db_alias).filter(
                normalized_name=normalized_name
            ).first()
            if key is None:
                key = SpecificationKey.objects.using(db_alias).create(
                    name=name,
                    normalized_name=normalized_name,
                    slug=unique_slug(SpecificationKey, name, db_alias),
                )
            seen_normalized_names.add(normalized_name)
            rows.append(
                ProductSpecification(
                    product_id=product.pk,
                    key_id=key.pk,
                    value=value,
                    position=position,
                )
            )
        ProductSpecification.objects.using(db_alias).bulk_create(rows)


def restore_legacy_specs(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductSpecification = apps.get_model("catalog", "ProductSpecification")
    db_alias = schema_editor.connection.alias
    by_product = {}
    rows = (
        ProductSpecification.objects.using(db_alias)
        .select_related("key")
        .order_by("product_id", "position", "id")
    )
    for row in rows.iterator():
        by_product.setdefault(row.product_id, []).append(
            {"label": row.key.name, "value": row.value}
        )
    for product_id, specs in by_product.items():
        Product.objects.using(db_alias).filter(pk=product_id).update(specs=specs)


class Migration(migrations.Migration):
    dependencies = [("catalog", "0011_brand_product_brand")]

    operations = [
        migrations.CreateModel(
            name="SpecificationKey",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="نام")),
                (
                    "normalized_name",
                    models.CharField(
                        editable=False,
                        max_length=100,
                        unique=True,
                        verbose_name="نام یکتاشده",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        allow_unicode=True,
                        blank=True,
                        max_length=120,
                        unique=True,
                        verbose_name="نامک",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="ایجاد")),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="به‌روزرسانی"),
                ),
            ],
            options={
                "verbose_name": "کلید مشخصه",
                "verbose_name_plural": "کلیدهای مشخصات",
                "ordering": ["name", "id"],
            },
        ),
        migrations.CreateModel(
            name="ProductSpecification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.CharField(max_length=500, verbose_name="مقدار")),
                (
                    "position",
                    models.PositiveIntegerField(default=0, verbose_name="ترتیب"),
                ),
                (
                    "key",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="product_specifications",
                        to="catalog.specificationkey",
                        verbose_name="کلید مشخصه",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="specifications",
                        to="catalog.product",
                        verbose_name="محصول",
                    ),
                ),
            ],
            options={
                "verbose_name": "مشخصه محصول",
                "verbose_name_plural": "مشخصات محصول",
                "ordering": ["position", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("product", "key"),
                        name="catalog_unique_product_spec_key",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("value", ""), _negated=True),
                        name="catalog_product_spec_value_nonempty",
                    ),
                ],
            },
        ),
        migrations.RunPython(migrate_legacy_specs, restore_legacy_specs),
        migrations.RemoveField(model_name="product", name="specs"),
    ]
