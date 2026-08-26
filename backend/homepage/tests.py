import shutil
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Brand, Category, Product

from .models import Banner, HomepageSection
from .services import (
    HomepageValidationError,
    create_banner,
    create_section,
    delete_section,
    move_section,
    section_products,
    section_products_total,
    update_section,
)


def make_image_file(name="banner.png", size=(10, 10)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class TempMediaRootMixin:
    """آپلودهای تست در پوشه‌ی موقت بنویسند، نه در media واقعی پروژه"""

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="homepage-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)


class HomepageModelTests(TestCase):
    def test_banner_section_requires_a_banner(self):
        section = HomepageSection(section_type=HomepageSection.SectionType.BANNER)
        with self.assertRaises(ValidationError):
            section.save()

    def test_non_product_collection_rejects_category_reference(self):
        category = Category.objects.create(slug="tools", title="ابزار")
        section = HomepageSection(
            section_type=HomepageSection.SectionType.BEST_SELLERS,
            category=category,
        )
        with self.assertRaises(ValidationError):
            section.save()

    def test_limit_must_be_within_bounds(self):
        section = HomepageSection(
            section_type=HomepageSection.SectionType.NEW_PRODUCTS, limit=100
        )
        with self.assertRaises(ValidationError):
            section.save()

    def test_banner_requires_matching_link_url_and_label(self):
        banner = Banner(title="بنر", link_url="/category/tools")
        with self.assertRaises(ValidationError):
            banner.save()

    def test_banner_rejects_unsafe_or_malformed_link(self):
        for link in ("javascript:alert(1)", "//example.com", "httpish"):
            with self.subTest(link=link), self.assertRaises(ValidationError):
                Banner(title="بنر", link_url=link, link_label="مشاهده").save()

    def test_unknown_section_type_rejected(self):
        section = HomepageSection(section_type="not_a_real_type")
        with self.assertRaises(ValidationError):
            section.save()


class HomepageServiceTests(TestCase):
    def setUp(self):
        HomepageSection.objects.all().delete()
        Banner.objects.all().delete()
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.brand = Brand.objects.create(name="برند الف", slug="a")

    def test_create_appends_at_the_end_and_delete_renumbers(self):
        first = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        second = create_section(section_type=HomepageSection.SectionType.BRANDS)
        third = create_section(section_type=HomepageSection.SectionType.NEW_PRODUCTS)
        self.assertEqual([first.position, second.position, third.position], [0, 1, 2])

        delete_section(second)
        third.refresh_from_db()
        self.assertEqual(third.position, 1)
        self.assertEqual(HomepageSection.objects.count(), 2)

    def test_move_up_and_down_swaps_neighbors(self):
        first = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        second = create_section(section_type=HomepageSection.SectionType.BRANDS)

        move_section(second, "up")
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(second.position, 0)
        self.assertEqual(first.position, 1)

        # already at top — moving up again is a no-op, not an error
        move_section(second, "up")
        second.refresh_from_db()
        self.assertEqual(second.position, 0)

    def test_update_section_revalidates(self):
        section = create_section(section_type=HomepageSection.SectionType.NEW_PRODUCTS)
        with self.assertRaises(HomepageValidationError):
            update_section(section, limit=999)

    def test_section_products_best_sellers_uses_curated_flag(self):
        Product.objects.create(
            title="عادی", category=self.category, price=1000, is_active=True
        )
        curated = Product.objects.create(
            title="پرفروش",
            category=self.category,
            price=1000,
            is_active=True,
            is_best_seller=True,
        )
        section = create_section(
            section_type=HomepageSection.SectionType.BEST_SELLERS
        )
        self.assertEqual(section_products(section), [curated])

    def test_every_product_section_type_is_exposed_publicly(self):
        """هیچ نوع بخش محصولی نباید بی‌سروصدا از پاسخ عمومی حذف شود"""
        from homepage.dto import public_section_dto
        from homepage.services import PRODUCT_SECTION_FILTERS

        for section_type in PRODUCT_SECTION_FILTERS:
            with self.subTest(section_type=section_type):
                section = create_section(section_type=section_type)
                dto = public_section_dto(section)
                self.assertIsNotNone(dto)
                self.assertEqual(dto["type"], section_type)
                self.assertIn("products", dto["data"])

    def test_all_products_page_is_limited_but_total_counts_catalog(self):
        """بخش «همه محصولات»: limit یعنی اندازه‌ی صفحه، نه سقف کل کاتالوگ"""
        for index in range(5):
            Product.objects.create(
                title=f"کالا {index}",
                category=self.category,
                price=1000,
                is_active=True,
            )
        Product.objects.create(
            title="غیرفعال", category=self.category, price=1000, is_active=False
        )
        section = create_section(
            section_type=HomepageSection.SectionType.ALL_PRODUCTS, limit=2
        )

        self.assertEqual(len(section_products(section)), 2)
        self.assertEqual(section_products_total(section), 5)

    def test_section_products_incredible_uses_curated_flag(self):
        """بخش شگفت‌انگیزها منتخب مدیر است، نه هر محصول تخفیف‌دار"""
        Product.objects.create(
            title="تخفیف‌دار انتخاب‌نشده",
            category=self.category,
            price=1000,
            old_price=2000,
            is_active=True,
        )
        curated = Product.objects.create(
            title="شگفت‌انگیز منتخب",
            category=self.category,
            price=1000,
            is_active=True,
            is_incredible=True,
        )
        section = create_section(
            section_type=HomepageSection.SectionType.INCREDIBLE_PRODUCTS
        )
        self.assertEqual(section_products(section), [curated])

    def test_section_products_discounted_lists_every_discounted_product(self):
        """بخش تخفیف‌ها مستقل از انتخاب مدیر، همه‌ی تخفیف‌دارها را می‌آورد"""
        discounted = Product.objects.create(
            title="تخفیف‌دار",
            category=self.category,
            price=1000,
            old_price=2000,
            is_active=True,
        )
        Product.objects.create(
            title="بدون تخفیف", category=self.category, price=1000, is_active=True
        )
        section = create_section(
            section_type=HomepageSection.SectionType.DISCOUNTED_PRODUCTS
        )
        self.assertEqual(section_products(section), [discounted])

    def test_section_products_product_collection_filters_by_brand(self):
        other_brand = Brand.objects.create(name="برند ب", slug="b")
        matching = Product.objects.create(
            title="محصول برند الف",
            category=self.category,
            brand=self.brand,
            price=1000,
        )
        Product.objects.create(
            title="محصول برند ب",
            category=self.category,
            brand=other_brand,
            price=1000,
        )
        section = create_section(
            section_type=HomepageSection.SectionType.PRODUCT_COLLECTION,
            brand=self.brand,
        )
        self.assertEqual(section_products(section), [matching])

    def test_section_products_empty_when_no_match(self):
        section = create_section(
            section_type=HomepageSection.SectionType.DISCOUNTED_PRODUCTS
        )
        self.assertEqual(section_products(section), [])

    def test_deleting_collection_filter_removes_section_instead_of_broadening_it(self):
        section = create_section(
            section_type=HomepageSection.SectionType.PRODUCT_COLLECTION,
            category=self.category,
        )

        self.category.delete()

        self.assertFalse(HomepageSection.objects.filter(pk=section.pk).exists())

    def test_create_appends_after_position_gap_from_cascade(self):
        first = create_section(section_type=HomepageSection.SectionType.BRANDS)
        collection = create_section(
            section_type=HomepageSection.SectionType.PRODUCT_COLLECTION,
            category=self.category,
        )
        last = create_section(section_type=HomepageSection.SectionType.NEW_PRODUCTS)
        self.category.delete()

        appended = create_section(section_type=HomepageSection.SectionType.CATEGORIES)

        self.assertFalse(HomepageSection.objects.filter(pk=collection.pk).exists())
        self.assertEqual(first.position, 0)
        self.assertEqual(last.position, 2)
        self.assertEqual(appended.position, 3)


class HomepageAdminApiTests(TempMediaRootMixin, TestCase):
    def setUp(self):
        HomepageSection.objects.all().delete()
        Banner.objects.all().delete()
        admin = get_user_model().objects.create_user(
            phone="09121234567", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(admin)
        self.category = Category.objects.create(slug="tools", title="ابزار")

    def test_non_staff_is_forbidden(self):
        client = APIClient()
        client.force_authenticate(get_user_model().objects.create_user(phone="09120000000"))
        response = client.get("/api/admin/home/sections")
        self.assertEqual(response.status_code, 403)

    def test_create_categories_section(self):
        response = self.client.post(
            "/api/admin/home/sections", {"sectionType": "categories"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["section"]["sectionType"], "categories")
        self.assertEqual(response.data["data"]["section"]["position"], 0)

    def test_create_recently_viewed_section(self):
        response = self.client.post(
            "/api/admin/home/sections",
            {"sectionType": "recently_viewed", "limit": 12},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        section = response.data["data"]["section"]
        self.assertEqual(section["sectionType"], "recently_viewed")
        self.assertEqual(section["resolvedTitle"], "محصولات اخیراً مشاهده‌شده")
        self.assertEqual(section["resolvedLimit"], 12)

    def test_create_all_products_section(self):
        response = self.client.post(
            "/api/admin/home/sections",
            {"sectionType": "all_products", "limit": 8},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        section = response.data["data"]["section"]
        self.assertEqual(section["sectionType"], "all_products")
        self.assertEqual(section["resolvedTitle"], "همه محصولات")
        self.assertEqual(section["resolvedLimit"], 8)

    def test_create_banner_section_requires_banner_id(self):
        response = self.client.post(
            "/api/admin/home/sections", {"sectionType": "banner"}, format="json"
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("bannerId", response.data["data"]["fieldErrors"])

    def test_create_banner_section_with_unknown_banner_id_fails(self):
        response = self.client.post(
            "/api/admin/home/sections",
            {"sectionType": "banner", "bannerId": 999},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_section_type_rejected(self):
        response = self.client.post(
            "/api/admin/home/sections", {"sectionType": "not_real"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_product_collection_rejects_unrelated_category_field_via_type_switch(self):
        # sectionType cannot be changed on update
        section = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        response = self.client.patch(
            f"/api/admin/home/sections/{section.id}",
            {"sectionType": "brands"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_title_and_toggle_active(self):
        section = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        response = self.client.patch(
            f"/api/admin/home/sections/{section.id}",
            {"title": "دسته‌های ما", "isActive": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["section"]["title"], "دسته‌های ما")
        self.assertFalse(response.data["data"]["section"]["isActive"])

    def test_delete_section(self):
        section = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        response = self.client.delete(f"/api/admin/home/sections/{section.id}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(HomepageSection.objects.filter(pk=section.id).exists())

    def test_move_endpoint_reorders(self):
        first = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        second = create_section(section_type=HomepageSection.SectionType.BRANDS)
        response = self.client.post(
            f"/api/admin/home/sections/{second.id}/move",
            {"direction": "up"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        positions = {
            item["id"]: item["position"] for item in response.data["data"]["sections"]
        }
        self.assertEqual(positions[second.id], 0)
        self.assertEqual(positions[first.id], 1)

    def test_banner_crud_and_image_upload(self):
        create_response = self.client.post(
            "/api/admin/home/banners",
            {"title": "بنر اصلی", "linkUrl": "/category/tools", "linkLabel": "مشاهده"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        banner_id = create_response.data["data"]["banner"]["id"]

        upload_response = self.client.post(
            f"/api/admin/home/banners/{banner_id}/image/desktop",
            {"file": make_image_file()},
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, 201)
        self.assertIsNotNone(upload_response.data["data"]["banner"]["desktopImage"])

        section_response = self.client.post(
            "/api/admin/home/sections",
            {"sectionType": "banner", "bannerId": banner_id},
            format="json",
        )
        self.assertEqual(section_response.status_code, 201)

        delete_response = self.client.delete(f"/api/admin/home/banners/{banner_id}")
        self.assertEqual(delete_response.status_code, 200)

        # section survives; banner reference gracefully nulled
        section = HomepageSection.objects.get(
            pk=section_response.data["data"]["section"]["id"]
        )
        self.assertIsNone(section.banner_id)

    def test_each_banner_image_variant_is_stored_separately(self):
        """تصویر موبایل نسخه‌ی جدا است، نه همان فایل دسکتاپ"""
        banner = create_banner(title="بنر دو تصویری")

        desktop = self.client.post(
            f"/api/admin/home/banners/{banner.id}/image/desktop",
            {"file": make_image_file("desktop.png", size=(1200, 400))},
            format="multipart",
        )
        mobile = self.client.post(
            f"/api/admin/home/banners/{banner.id}/image/mobile",
            {"file": make_image_file("mobile.png", size=(400, 500))},
            format="multipart",
        )

        self.assertEqual(desktop.status_code, 201)
        self.assertEqual(mobile.status_code, 201)
        data = mobile.data["data"]["banner"]
        self.assertIsNotNone(data["desktopImage"])
        self.assertIsNotNone(data["mobileImage"])
        self.assertNotEqual(data["desktopImage"], data["mobileImage"])

        banner.refresh_from_db()
        self.assertIn("desktop", banner.desktop_image.name)
        self.assertIn("mobile", banner.mobile_image.name)

    def test_deleting_one_image_variant_keeps_the_other(self):
        banner = create_banner(title="بنر")
        for variant in ("desktop", "mobile"):
            self.client.post(
                f"/api/admin/home/banners/{banner.id}/image/{variant}",
                {"file": make_image_file(f"{variant}.png")},
                format="multipart",
            )

        response = self.client.delete(
            f"/api/admin/home/banners/{banner.id}/image/mobile"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["banner"]["mobileImage"])
        self.assertIsNotNone(response.data["data"]["banner"]["desktopImage"])

    def test_unknown_image_variant_is_rejected(self):
        banner = create_banner(title="بنر")
        response = self.client.post(
            f"/api/admin/home/banners/{banner.id}/image/tablet",
            {"file": make_image_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 404)

    def test_replacing_an_image_variant_only_touches_that_variant(self):
        banner = create_banner(title="بنر")
        self.client.post(
            f"/api/admin/home/banners/{banner.id}/image/desktop",
            {"file": make_image_file("desktop.png")},
            format="multipart",
        )
        banner.refresh_from_db()
        desktop_name = banner.desktop_image.name

        self.client.post(
            f"/api/admin/home/banners/{banner.id}/image/mobile",
            {"file": make_image_file("mobile.png")},
            format="multipart",
        )

        banner.refresh_from_db()
        self.assertEqual(banner.desktop_image.name, desktop_name)

    def test_banner_link_validation(self):
        response = self.client.post(
            "/api/admin/home/banners",
            {"title": "بنر", "linkUrl": "/category/tools"},
            format="json",
        )
        self.assertEqual(response.status_code, 422)


class HomepagePublicApiTests(TempMediaRootMixin, TestCase):
    def setUp(self):
        HomepageSection.objects.all().delete()
        Banner.objects.all().delete()
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.client = APIClient()

    def test_only_active_sections_are_returned_in_order(self):
        create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        inactive = create_section(section_type=HomepageSection.SectionType.BRANDS)
        update_section(inactive, is_active=False)
        create_section(section_type=HomepageSection.SectionType.NEW_PRODUCTS)

        response = self.client.get("/api/home/sections")
        self.assertEqual(response.status_code, 200)
        types = [item["type"] for item in response.data["data"]["sections"]]
        self.assertEqual(types, ["categories", "new_products"])

    def test_reordering_is_reflected_immediately(self):
        first = create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        second = create_section(section_type=HomepageSection.SectionType.BRANDS)
        move_section(second, "up")

        response = self.client.get("/api/home/sections")
        types = [item["type"] for item in response.data["data"]["sections"]]
        self.assertEqual(types, ["brands", "categories"])

    def test_multiple_sections_of_the_same_type_are_all_returned(self):
        create_section(section_type=HomepageSection.SectionType.NEW_PRODUCTS, title="الف")
        create_section(section_type=HomepageSection.SectionType.NEW_PRODUCTS, title="ب")

        response = self.client.get("/api/home/sections")
        titles = [item["title"] for item in response.data["data"]["sections"]]
        self.assertEqual(titles, ["الف", "ب"])

    def test_multiple_banner_sections_are_returned_in_order(self):
        first = create_banner(title="بنر اول")
        second = create_banner(title="بنر دوم")
        create_section(
            section_type=HomepageSection.SectionType.BANNER, banner=first
        )
        create_section(
            section_type=HomepageSection.SectionType.BANNER, banner=second
        )

        response = self.client.get("/api/home/sections")

        banner_ids = [
            item["data"]["banner"]["id"]
            for item in response.data["data"]["sections"]
        ]
        self.assertEqual(banner_ids, [first.id, second.id])

    def test_banner_section_exposes_both_image_variants(self):
        """فروشگاه باید هر دو نسخه را بگیرد تا خودش مناسب نمایشگر را انتخاب کند"""
        banner = create_banner(
            title="بنر واکنش‌گرا",
            desktop_image=make_image_file("wide.png", size=(1200, 400)),
            mobile_image=make_image_file("narrow.png", size=(400, 500)),
        )
        create_section(
            section_type=HomepageSection.SectionType.BANNER, banner=banner
        )

        response = self.client.get("/api/home/sections")

        data = response.data["data"]["sections"][0]["data"]["banner"]
        self.assertIsNotNone(data["desktopImage"])
        self.assertIsNotNone(data["mobileImage"])
        self.assertNotEqual(data["desktopImage"], data["mobileImage"])

    def test_banner_without_mobile_image_still_reports_the_desktop_one(self):
        """بنرهای قدیمی فقط تصویر دسکتاپ دارند و نباید بشکنند"""
        banner = create_banner(
            title="بنر قدیمی", desktop_image=make_image_file("legacy.png")
        )
        create_section(
            section_type=HomepageSection.SectionType.BANNER, banner=banner
        )

        response = self.client.get("/api/home/sections")

        data = response.data["data"]["sections"][0]["data"]["banner"]
        self.assertIsNotNone(data["desktopImage"])
        self.assertIsNone(data["mobileImage"])

    def test_banner_section_with_deleted_banner_is_skipped(self):
        banner = create_banner(title="بنر موقت")
        section = create_section(
            section_type=HomepageSection.SectionType.BANNER, banner=banner
        )
        banner.delete()

        response = self.client.get("/api/home/sections")
        self.assertEqual(response.data["data"]["sections"], [])
        # section itself still exists — admin can fix or delete it
        self.assertTrue(HomepageSection.objects.filter(pk=section.id).exists())

    def test_product_section_with_no_matches_still_included_with_empty_list(self):
        create_section(section_type=HomepageSection.SectionType.DISCOUNTED_PRODUCTS)

        response = self.client.get("/api/home/sections")
        sections = response.data["data"]["sections"]
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]["data"]["products"], [])

    def test_default_title_used_when_no_custom_title_set(self):
        create_section(section_type=HomepageSection.SectionType.BEST_SELLERS)

        response = self.client.get("/api/home/sections")
        self.assertEqual(response.data["data"]["sections"][0]["title"], "پرفروش‌ترین‌ها")

    def test_custom_title_overrides_default(self):
        create_section(
            section_type=HomepageSection.SectionType.BEST_SELLERS,
            title="منتخب فروشگاه",
        )

        response = self.client.get("/api/home/sections")
        self.assertEqual(
            response.data["data"]["sections"][0]["title"], "منتخب فروشگاه"
        )

    def test_categories_section_only_lists_root_categories(self):
        sub = Category.objects.create(slug="sub", title="زیرشاخه")
        sub.parents.add(self.category)
        create_section(section_type=HomepageSection.SectionType.CATEGORIES)

        response = self.client.get("/api/home/sections")
        slugs = [
            item["slug"] for item in response.data["data"]["sections"][0]["data"]["categories"]
        ]
        self.assertEqual(slugs, ["tools"])

    def test_public_section_includes_stable_id(self):
        section = create_section(section_type=HomepageSection.SectionType.CATEGORIES)

        response = self.client.get("/api/home/sections")

        self.assertEqual(response.data["data"]["sections"][0]["id"], section.id)

    def test_recently_viewed_section_exposes_config_without_server_history(self):
        create_section(
            section_type=HomepageSection.SectionType.RECENTLY_VIEWED,
            limit=12,
        )

        response = self.client.get("/api/home/sections")

        self.assertEqual(response.status_code, 200)
        section = response.data["data"]["sections"][0]
        self.assertEqual(section["type"], "recently_viewed")
        self.assertEqual(section["title"], "محصولات اخیراً مشاهده‌شده")
        self.assertEqual(section["limit"], 12)
        self.assertEqual(section["data"], {})

    def test_all_products_section_exposes_first_page_and_total(self):
        """فروشگاه برای صفحه‌بندی، هم کالاهای صفحه‌ی اول را می‌خواهد هم تعداد کل"""
        for index in range(4):
            Product.objects.create(
                title=f"کالا {index}",
                category=self.category,
                price=1000,
                is_active=True,
            )
        create_section(
            section_type=HomepageSection.SectionType.ALL_PRODUCTS, limit=3
        )

        response = self.client.get("/api/home/sections")

        self.assertEqual(response.status_code, 200)
        section = response.data["data"]["sections"][0]
        self.assertEqual(section["type"], "all_products")
        self.assertEqual(section["title"], "همه محصولات")
        self.assertEqual(section["limit"], 3)
        self.assertEqual(len(section["data"]["products"]), 3)
        self.assertEqual(section["data"]["total"], 4)

    def test_all_products_section_can_be_moved_like_any_other(self):
        """جای بخش از پنل مدیریت عوض می‌شود — همان مسیر بقیه‌ی بخش‌ها"""
        create_section(section_type=HomepageSection.SectionType.CATEGORIES)
        all_products = create_section(
            section_type=HomepageSection.SectionType.ALL_PRODUCTS
        )
        move_section(all_products, "up")

        response = self.client.get("/api/home/sections")

        types = [item["type"] for item in response.data["data"]["sections"]]
        self.assertEqual(types, ["all_products", "categories"])
