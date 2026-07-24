from django.db import migrations, models
from django.db.models import Count


def ensure_no_duplicate_reviews(apps, schema_editor):
    review = apps.get_model("catalog", "Review")
    has_duplicates = (
        review.objects.values("user_id", "product_id")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
        .exists()
    )
    if has_duplicates:
        raise RuntimeError(
            "Duplicate product reviews exist. Resolve duplicate rows before "
            "applying catalog.0003_review_unique_user_product."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_productimage"),
    ]

    operations = [
        migrations.RunPython(
            ensure_no_duplicate_reviews, reverse_code=migrations.RunPython.noop
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.UniqueConstraint(
                fields=("user", "product"),
                name="unique_user_product_review",
            ),
        ),
    ]
