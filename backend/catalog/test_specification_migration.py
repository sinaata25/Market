from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class LegacySpecificationMigrationTests(TransactionTestCase):
    migrate_from = ("catalog", "0011_brand_product_brand")
    migrate_to = ("catalog", "0012_normalized_product_specifications")

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Category = old_apps.get_model("catalog", "Category")
        Product = old_apps.get_model("catalog", "Product")
        category = Category.objects.create(slug="tools", title="ابزار")
        Product.objects.create(
            title="محصول A",
            category=category,
            price=100,
            specs=[
                {"label": "وزن كالا", "value": " 1 kg "},
                {"label": "ابعاد", "value": "20 × 30"},
            ],
        )
        Product.objects.create(
            title="محصول B",
            category=category,
            price=200,
            specs=[{"label": "وزن‌کالا", "value": "2 kg"}],
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_legacy_json_is_normalized_reused_and_removed(self):
        Product = self.apps.get_model("catalog", "Product")
        SpecificationKey = self.apps.get_model("catalog", "SpecificationKey")
        ProductSpecification = self.apps.get_model(
            "catalog", "ProductSpecification"
        )

        self.assertNotIn("specs", {field.name for field in Product._meta.fields})
        self.assertEqual(SpecificationKey.objects.count(), 2)
        weight = SpecificationKey.objects.get(normalized_name="وزن کالا")
        rows = ProductSpecification.objects.filter(key=weight).order_by("product_id")
        self.assertEqual(rows.count(), 2)
        self.assertEqual([row.value for row in rows], ["1 kg", "2 kg"])
        dimensions = ProductSpecification.objects.get(key__normalized_name="ابعاد")
        self.assertEqual(dimensions.position, 1)
