from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("homepage", "0007_all_products_section")]

    operations = [
        # تصویر موجود همان نسخه‌ی دسکتاپ است — rename تا بنرهای فعلی تصویرشان
        # را از دست ندهند
        migrations.RenameField(
            model_name="banner",
            old_name="image",
            new_name="desktop_image",
        ),
        migrations.AlterField(
            model_name="banner",
            name="desktop_image",
            field=models.ImageField(
                blank=True, upload_to="banners/", verbose_name="تصویر دسکتاپ"
            ),
        ),
        migrations.AddField(
            model_name="banner",
            name="mobile_image",
            field=models.ImageField(
                blank=True, upload_to="banners/mobile/", verbose_name="تصویر موبایل"
            ),
        ),
    ]
