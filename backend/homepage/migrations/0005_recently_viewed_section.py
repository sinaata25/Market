from django.db import migrations, models
from django.db.models import Max


def add_default_recently_viewed_section(apps, schema_editor):
    HomepageSection = apps.get_model("homepage", "HomepageSection")
    if HomepageSection.objects.filter(section_type="recently_viewed").exists():
        return
    last_position = HomepageSection.objects.aggregate(value=Max("position"))["value"]
    HomepageSection.objects.create(
        section_type="recently_viewed",
        title="",
        position=0 if last_position is None else last_position + 1,
        is_active=True,
        limit=10,
    )


class Migration(migrations.Migration):
    dependencies = [("homepage", "0004_safe_collection_reference_deletion")]

    operations = [
        migrations.AlterField(
            model_name="homepagesection",
            name="section_type",
            field=models.CharField(
                choices=[
                    ("banner", "بنر"),
                    ("categories", "دسته‌بندی‌ها"),
                    ("brands", "برندها"),
                    ("best_sellers", "پرفروش‌ترین‌ها"),
                    ("discounted_products", "تخفیف‌های ویژه"),
                    ("new_products", "جدیدترین محصولات"),
                    ("product_collection", "مجموعه محصولات سفارشی"),
                    ("recently_viewed", "محصولات اخیراً مشاهده‌شده"),
                ],
                max_length=32,
                verbose_name="نوع بخش",
            ),
        ),
        migrations.RunPython(
            add_default_recently_viewed_section, migrations.RunPython.noop
        ),
    ]
