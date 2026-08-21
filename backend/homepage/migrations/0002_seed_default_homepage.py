from django.db import migrations


def seed_default_homepage(apps, schema_editor):
    Banner = apps.get_model("homepage", "Banner")
    HomepageSection = apps.get_model("homepage", "HomepageSection")

    if HomepageSection.objects.exists():
        return

    banner = Banner.objects.create(
        title="هر آنچه برای کشاورزی نیاز دارید، یکجا",
        subtitle=(
            "از بیل و قیچی باغبانی تا سمپاش و اره‌موتوری؛ با ضمانت اصالت "
            "کالا و ارسال سریع به سراسر کشور."
        ),
        theme="brand",
        link_url="/category/garden-tools",
        link_label="مشاهده محصولات",
        is_active=True,
    )
    HomepageSection.objects.bulk_create(
        [
            HomepageSection(section_type="banner", banner=banner, position=0),
            HomepageSection(section_type="categories", position=1, limit=8),
            HomepageSection(
                section_type="discounted_products", position=2, limit=6
            ),
            HomepageSection(section_type="best_sellers", position=3, limit=8),
        ]
    )


class Migration(migrations.Migration):
    dependencies = [("homepage", "0001_initial")]

    operations = [
        # Reversing must not delete content that an admin may have edited after deploy.
        migrations.RunPython(seed_default_homepage, migrations.RunPython.noop),
    ]
