from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0009_category_parents_remove_sub"),
    ]

    operations = [
        # Preserve the current public visibility of reviews already in production.
        migrations.AddField(
            model_name="review",
            name="is_published",
            field=models.BooleanField(default=True, verbose_name="منتشر شده"),
        ),
        migrations.AlterField(
            model_name="review",
            name="is_published",
            field=models.BooleanField(default=False, verbose_name="منتشر شده"),
        ),
    ]
