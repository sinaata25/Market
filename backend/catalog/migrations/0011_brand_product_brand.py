import django.db.models.deletion
from django.db import migrations, models
import catalog.validators


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_separate_ratings_and_comments"),
    ]

    operations = [
        migrations.CreateModel(
            name="Brand",
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
                ("name", models.CharField(max_length=100, unique=True, verbose_name="نام")),
                ("slug", models.SlugField(max_length=100, unique=True, verbose_name="نامک")),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                (
                    "logo",
                    models.FileField(
                        blank=True,
                        help_text="فایل PNG یا SVG ایمن، حداکثر ۵ مگابایت",
                        upload_to="brands/logos/",
                        validators=[catalog.validators.validate_category_icon],
                        verbose_name="نشان تجاری",
                    ),
                ),
                ("website", models.URLField(blank=True, verbose_name="وب‌سایت")),
                ("is_active", models.BooleanField(default=True, verbose_name="نمایش در فروشگاه")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="به‌روزرسانی")),
            ],
            options={
                "verbose_name": "برند",
                "verbose_name_plural": "برندها",
                "ordering": ["name", "id"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="catalog.brand",
                verbose_name="برند",
            ),
        ),
    ]
