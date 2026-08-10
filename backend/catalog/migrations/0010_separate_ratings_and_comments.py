import django.db.models.deletion
import django.utils.timezone
import django.core.validators
from django.conf import settings
from django.db import migrations, models
from django.db.models import Avg, Count


PURCHASED_STATUSES = ("PAID", "SHIPPED", "DELIVERED")


def migrate_eligible_ratings(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductComment = apps.get_model("catalog", "ProductComment")
    ProductRating = apps.get_model("catalog", "ProductRating")
    OrderItem = apps.get_model("orders", "OrderItem")

    for comment in ProductComment.objects.all().iterator():
        purchased = OrderItem.objects.filter(
            product_id=comment.product_id,
            order__user_id=comment.user_id,
            order__status__in=PURCHASED_STATUSES,
        ).exists()
        if purchased:
            ProductRating.objects.update_or_create(
                product_id=comment.product_id,
                user_id=comment.user_id,
                defaults={"rating": comment.rating},
            )

    Product.objects.update(rating=0, rating_count=0)
    aggregates = ProductRating.objects.values("product_id").annotate(
        average=Avg("rating"), count=Count("id")
    )
    for aggregate in aggregates:
        Product.objects.filter(pk=aggregate["product_id"]).update(
            rating=round(aggregate["average"] or 0, 1),
            rating_count=aggregate["count"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0009_category_parents_remove_sub"),
        ("orders", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Review",
            new_name="ProductComment",
        ),
        migrations.RemoveConstraint(
            model_name="productcomment",
            name="unique_user_product_review",
        ),
        migrations.RenameField(
            model_name="productcomment",
            old_name="text",
            new_name="content",
        ),
        migrations.AddField(
            model_name="productcomment",
            name="comment_type",
            field=models.CharField(
                choices=[("comment", "دیدگاه"), ("question", "پرسش")],
                default="comment",
                max_length=16,
                verbose_name="نوع",
            ),
        ),
        migrations.AddField(
            model_name="productcomment",
            name="moderation_status",
            field=models.CharField(
                choices=[
                    ("pending", "در انتظار تایید"),
                    ("approved", "تایید شده"),
                    ("rejected", "رد شده"),
                ],
                default="approved",
                max_length=16,
                verbose_name="وضعیت بررسی",
            ),
        ),
        migrations.AlterField(
            model_name="productcomment",
            name="moderation_status",
            field=models.CharField(
                choices=[
                    ("pending", "در انتظار تایید"),
                    ("approved", "تایید شده"),
                    ("rejected", "رد شده"),
                ],
                default="pending",
                max_length=16,
                verbose_name="وضعیت بررسی",
            ),
        ),
        migrations.AddField(
            model_name="productcomment",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="replies",
                to="catalog.productcomment",
                verbose_name="پاسخ به",
            ),
        ),
        migrations.AddField(
            model_name="productcomment",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=django.utils.timezone.now,
                verbose_name="به‌روزرسانی",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="productcomment",
            name="product",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to="catalog.product",
                verbose_name="محصول",
            ),
        ),
        migrations.AlterField(
            model_name="productcomment",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="product_comments",
                to=settings.AUTH_USER_MODEL,
                verbose_name="نویسنده",
            ),
        ),
        migrations.AlterModelOptions(
            name="productcomment",
            options={
                "ordering": ["created_at", "id"],
                "verbose_name": "دیدگاه محصول",
                "verbose_name_plural": "دیدگاه‌های محصول",
            },
        ),
        migrations.AddIndex(
            model_name="productcomment",
            index=models.Index(
                fields=["product", "moderation_status", "created_at"],
                name="comment_product_status_idx",
            ),
        ),
        migrations.CreateModel(
            name="ProductRating",
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
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                        verbose_name="امتیاز",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="به‌روزرسانی")),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ratings",
                        to="catalog.product",
                        verbose_name="محصول",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_ratings",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="کاربر",
                    ),
                ),
            ],
            options={
                "verbose_name": "امتیاز محصول",
                "verbose_name_plural": "امتیازهای محصول",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "product"),
                        name="unique_user_product_rating",
                    )
                ],
            },
        ),
        migrations.RunPython(
            migrate_eligible_ratings,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="productcomment",
            name="rating",
        ),
    ]
