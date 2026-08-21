import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("homepage", "0003_homepage_section_order_index")]

    operations = [
        migrations.AlterField(
            model_name="homepagesection",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="catalog.brand",
                verbose_name="برند",
            ),
        ),
        migrations.AlterField(
            model_name="homepagesection",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="catalog.category",
                verbose_name="دسته‌بندی",
            ),
        ),
    ]
