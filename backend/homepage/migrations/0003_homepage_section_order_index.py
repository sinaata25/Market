from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("homepage", "0002_seed_default_homepage")]

    operations = [
        migrations.AddIndex(
            model_name="homepagesection",
            index=models.Index(
                fields=["position", "id"], name="home_section_order_idx"
            ),
        ),
    ]
