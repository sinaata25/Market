import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0013_product_best_seller_position_product_is_best_seller"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductRecommendation",
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
                ("position", models.PositiveSmallIntegerField(verbose_name="ترتیب")),
                (
                    "recommended_product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommended_by_links",
                        to="catalog.product",
                        verbose_name="محصول پیشنهادی",
                    ),
                ),
                (
                    "source_product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendation_links",
                        to="catalog.product",
                        verbose_name="محصول اصلی",
                    ),
                ),
            ],
            options={
                "verbose_name": "محصول پیشنهادی",
                "verbose_name_plural": "محصولات پیشنهادی",
                "ordering": ["position", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("source_product", "recommended_product"),
                        name="catalog_unique_product_recommendation",
                    ),
                    models.UniqueConstraint(
                        fields=("source_product", "position"),
                        name="catalog_unique_recommendation_position",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("source_product", models.F("recommended_product")),
                            _negated=True,
                        ),
                        name="catalog_recommendation_not_self",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("position__lte", 2)),
                        name="catalog_recommendation_position_max_three",
                    ),
                ],
            },
        ),
    ]
