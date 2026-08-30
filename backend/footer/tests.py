import shutil
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from seo.models import SeoSettings
from staticpages.models import StaticPage
from staticpages.definitions import default_content, default_section_visibility

from .dto import item_dto, settings_dto
from .models import FooterItem, FooterSection, FooterSettings
from .services import (
    FooterValidationError,
    create_item,
    create_section,
    delete_item,
    delete_section,
    move_item,
    move_section,
    update_item,
    update_section,
    update_settings,
)


def make_image_file(name="logo.png", size=(10, 10)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "green").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class TempMediaRootMixin:
    """آپلودهای تست در پوشه‌ی موقت بنویسند، نه در media واقعی پروژه"""

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="footer-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)


class FooterResetMixin:
    """داده‌های seed مهاجرت نباید نتیجه‌ی تست‌ها را جابه‌جا کند"""

    def setUp(self):
        super().setUp()
        FooterSection.objects.all().delete()
        FooterSettings.objects.all().delete()


def make_section(**fields) -> FooterSection:
    return create_section(**{"title": "خدمات مشتریان", **fields})


def make_link(section: FooterSection, **fields) -> FooterItem:
    return create_item(
        section=section,
        **{"item_type": "link", "label": "پرسش‌ها", "url": "/support", **fields},
    )


# ───────────────────────────────── مدل و اعتبارسنجی ─────────────────────────


class FooterModelTests(FooterResetMixin, TestCase):
    def test_a_column_section_needs_a_title(self):
        with self.assertRaises(ValidationError):
            FooterSection(variant="column", title="").save()

    def test_the_feature_strip_may_stay_untitled(self):
        FooterSection(variant="strip", title="").save()
        self.assertEqual(FooterSection.objects.count(), 1)

    def test_a_link_without_a_destination_is_rejected(self):
        section = make_section()
        with self.assertRaises(ValidationError):
            FooterItem(section=section, item_type="link", label="بدون مقصد").save()

    def test_a_link_url_must_be_an_internal_path_or_http_address(self):
        section = make_section()
        for url in ("javascript:alert(1)", "//evil.example", "ftp://x.example"):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                FooterItem(
                    section=section, item_type="link", label="بد", url=url
                ).save()

    def test_internal_and_external_links_are_both_accepted(self):
        section = make_section()
        for url in ("/support", "https://instagram.com/shop"):
            with self.subTest(url=url):
                FooterItem(
                    section=section, item_type="link", label="خوب", url=url
                ).save()

    def test_html_is_rejected_everywhere_footer_text_is_stored(self):
        section = make_section()
        with self.assertRaises(ValidationError):
            FooterItem(
                section=section,
                item_type="text",
                text="<script>alert(1)</script>",
            ).save()
        with self.assertRaises(ValidationError):
            FooterSection(variant="column", title="<b>عنوان</b>").save()
        with self.assertRaises(ValidationError):
            FooterSettings(pk=1, description="<img src=x onerror=1>").save()

    def test_a_field_that_does_not_belong_to_the_item_type_is_rejected(self):
        section = make_section()
        with self.assertRaises(ValidationError):
            FooterItem(
                section=section, item_type="text", text="متن", url="/support"
            ).save()

    def test_phone_and_email_items_validate_their_value(self):
        section = make_section()
        with self.assertRaises(ValidationError):
            FooterItem(section=section, item_type="phone", text="۱۲").save()
        with self.assertRaises(ValidationError):
            FooterItem(section=section, item_type="email", text="not-an-email").save()
        FooterItem(section=section, item_type="phone", text="۰۲۱-۱۲۳۴۵۶۷۸").save()
        FooterItem(section=section, item_type="email", text="info@example.com").save()

    def test_an_unknown_static_page_key_is_rejected(self):
        section = make_section()
        with self.assertRaises(ValidationError):
            FooterItem(
                section=section,
                item_type="link",
                label="نامعتبر",
                url="/x",
                static_page_key="not-a-page",
            ).save()

    def test_settings_reject_an_invalid_phone_or_email(self):
        with self.assertRaises(ValidationError):
            FooterSettings(pk=1, phone="abc").save()
        with self.assertRaises(ValidationError):
            FooterSettings(pk=1, email="a@@b").save()

    def test_settings_are_a_single_row_that_always_exists(self):
        first = FooterSettings.load()
        self.assertEqual(FooterSettings.load().pk, first.pk)
        self.assertEqual(FooterSettings.objects.count(), 1)


# ─────────────────────────────────── سرویس‌ها ────────────────────────────────


class FooterOrderingTests(FooterResetMixin, TestCase):
    def test_new_sections_are_appended_to_the_end(self):
        first = make_section(title="یک")
        second = make_section(title="دو")
        self.assertEqual([first.position, second.position], [0, 1])

    def test_moving_a_section_swaps_it_with_its_neighbour(self):
        first = make_section(title="یک")
        second = make_section(title="دو")
        move_section(second, "up")
        self.assertEqual(
            [section.title for section in FooterSection.objects.all()], ["دو", "یک"]
        )

    def test_moving_past_an_edge_changes_nothing(self):
        first = make_section(title="یک")
        make_section(title="دو")
        move_section(first, "up")
        self.assertEqual(
            [section.title for section in FooterSection.objects.all()], ["یک", "دو"]
        )

    def test_deleting_a_section_closes_the_gap_in_positions(self):
        first = make_section(title="یک")
        second = make_section(title="دو")
        third = make_section(title="سه")
        delete_section(second)
        self.assertEqual(
            [section.position for section in FooterSection.objects.all()], [0, 1]
        )
        self.assertEqual(
            [section.title for section in FooterSection.objects.all()], ["یک", "سه"]
        )

    def test_item_positions_are_scoped_to_their_own_section(self):
        first = make_section(title="یک")
        second = make_section(title="دو")
        make_link(first, label="الف")
        make_link(second, label="ب")
        self.assertEqual(
            [item.position for item in FooterItem.objects.order_by("id")], [0, 0]
        )

    def test_moving_an_item_only_reorders_its_own_section(self):
        section = make_section()
        other = make_section(title="دیگر")
        untouched = make_link(other, label="دست‌نخورده")
        first = make_link(section, label="الف")
        second = make_link(section, label="ب")
        move_item(second, "up")
        self.assertEqual(
            [item.label for item in section.items.all()], ["ب", "الف"]
        )
        untouched.refresh_from_db()
        self.assertEqual(untouched.position, 0)

    def test_deleting_an_item_closes_the_gap_in_positions(self):
        section = make_section()
        make_link(section, label="الف")
        middle = make_link(section, label="ب")
        make_link(section, label="ج")
        delete_item(middle)
        self.assertEqual([item.position for item in section.items.all()], [0, 1])


class FooterServiceTests(FooterResetMixin, TestCase):
    def test_changing_the_item_type_clears_fields_of_the_old_type(self):
        section = make_section()
        item = make_link(section, label="پیوند", url="/support", icon="🔗")
        update_item(item, item_type="text", text="یک توضیح")
        item.refresh_from_db()
        self.assertEqual(item.url, "")
        self.assertEqual(item.text, "یک توضیح")

    def test_an_invalid_update_raises_the_service_error_with_field_names(self):
        section = make_section()
        item = make_link(section)
        with self.assertRaises(FooterValidationError) as caught:
            update_item(item, url="javascript:alert(1)")
        self.assertIn("url", caught.exception.errors)

    def test_the_brand_title_falls_back_to_the_seo_site_name(self):
        seo = SeoSettings.load()
        seo.site_name = "نام سایت"
        seo.save(update_fields=["site_name"])
        settings_row = update_settings(brand_title="")
        self.assertEqual(settings_dto(settings_row)["brandTitle"], "نام سایت")

    def test_the_copyright_template_receives_the_year_and_brand(self):
        settings_row = update_settings(
            brand_title="فروشگاه", copyright_text="حقوق {year} — {brand}"
        )
        self.assertEqual(
            settings_dto(settings_row, year=1404)["copyright"],
            "حقوق 1404 — فروشگاه",
        )


class FooterDtoTests(FooterResetMixin, TestCase):
    def test_a_phone_item_exposes_a_dialable_destination(self):
        section = make_section()
        item = create_item(
            section=section, item_type="phone", text="۰۲۱-۱۲۳۴۵۶۷۸", label="تلفن"
        )
        self.assertEqual(item_dto(item)["url"], "tel:02112345678")

    def test_an_email_item_exposes_a_mailto_destination(self):
        section = make_section()
        item = create_item(
            section=section, item_type="email", text="info@example.com"
        )
        self.assertEqual(item_dto(item)["url"], "mailto:info@example.com")

    def test_external_links_are_marked_so_the_storefront_can_add_rel(self):
        section = make_section()
        internal = make_link(section, url="/support")
        external = make_link(section, label="اینستاگرام", url="https://x.example/a")
        self.assertFalse(item_dto(internal)["isExternal"])
        self.assertTrue(item_dto(external)["isExternal"])


# ──────────────────────────────── API عمومی ─────────────────────────────────


class FooterPublicApiTests(FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_the_whole_footer_arrives_in_one_request(self):
        section = make_section()
        make_link(section)
        response = self.client.get("/api/footer")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("settings", data)
        self.assertEqual(len(data["sections"]), 1)
        self.assertEqual(len(data["sections"][0]["items"]), 1)

    def test_inactive_sections_and_items_are_absent(self):
        hidden = make_section(title="پنهان", is_active=False)
        make_link(hidden)
        shown = make_section(title="پیدا")
        make_link(shown, label="دیده می‌شود")
        make_link(shown, label="پنهان", is_active=False)

        sections = self.client.get("/api/footer").json()["data"]["sections"]
        self.assertEqual([section["title"] for section in sections], ["پیدا"])
        self.assertEqual(
            [item["label"] for item in sections[0]["items"]], ["دیده می‌شود"]
        )

    def test_a_section_left_without_items_is_not_rendered_as_an_empty_column(self):
        section = make_section()
        make_link(section, is_active=False)
        self.assertEqual(self.client.get("/api/footer").json()["data"]["sections"], [])

    def test_sections_and_items_arrive_already_ordered(self):
        second = make_section(title="دو")
        first = make_section(title="یک")
        move_section(first, "up")
        make_link(first, label="تنها")
        make_link(second, label="ب")
        alpha = make_link(second, label="الف")
        move_item(alpha, "up")

        sections = self.client.get("/api/footer").json()["data"]["sections"]
        self.assertEqual([section["title"] for section in sections], ["یک", "دو"])
        self.assertEqual(
            [item["label"] for item in sections[1]["items"]], ["الف", "ب"]
        )

    def test_a_link_to_a_hidden_static_page_disappears_with_that_page(self):
        section = make_section()
        make_link(section, label="درباره ما", url="/about", static_page_key="about")
        make_link(section, label="وبلاگ", url="/blog")

        StaticPage.objects.update_or_create(
            key="about",
            defaults={
                "content": default_content("about"),
                "is_visible": False,
                "section_visibility": default_section_visibility("about"),
            },
        )
        sections = self.client.get("/api/footer").json()["data"]["sections"]
        self.assertEqual([item["label"] for item in sections[0]["items"]], ["وبلاگ"])

    def test_the_public_payload_never_leaks_management_only_fields(self):
        section = make_section()
        make_link(section, static_page_key="about", url="/about")
        payload = self.client.get("/api/footer").json()["data"]
        self.assertNotIn("isActive", payload["sections"][0])
        item = payload["sections"][0]["items"][0]
        for field in ("isActive", "staticPageKey", "rawUrl", "createdAt"):
            self.assertNotIn(field, item)

    def test_reading_the_footer_stays_on_a_constant_number_of_queries(self):
        """افزودن بخش و آیتم نباید کوئری اضافه بسازد — فوتر روی هر صفحه است"""
        FooterSettings.load()
        make_link(make_section(title="بخش تنها"))
        with CaptureQueriesContext(connection) as small:
            self.client.get("/api/footer")

        for index in range(5):
            section = make_section(title=f"بخش {index}")
            for _ in range(4):
                make_link(section)
        with CaptureQueriesContext(connection) as large:
            self.client.get("/api/footer")

        self.assertEqual(len(large), len(small))
        self.assertLessEqual(len(small), 6)

    def test_an_anonymous_visitor_may_not_write_anything(self):
        response = self.client.post("/api/footer", {"title": "x"})
        self.assertEqual(response.status_code, 405)


# ──────────────────────────────── API مدیریت ────────────────────────────────


class FooterAdminPermissionTests(FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.section = make_section()
        self.item = make_link(self.section)

    def _urls(self) -> list[tuple[str, str]]:
        return [
            ("get", "/api/admin/footer/settings"),
            ("patch", "/api/admin/footer/settings"),
            ("get", "/api/admin/footer/sections"),
            ("post", "/api/admin/footer/sections"),
            ("patch", f"/api/admin/footer/sections/{self.section.id}"),
            ("delete", f"/api/admin/footer/sections/{self.section.id}"),
            ("post", f"/api/admin/footer/sections/{self.section.id}/move"),
            ("post", f"/api/admin/footer/sections/{self.section.id}/items"),
            ("patch", f"/api/admin/footer/items/{self.item.id}"),
            ("delete", f"/api/admin/footer/items/{self.item.id}"),
            ("post", f"/api/admin/footer/items/{self.item.id}/move"),
            ("post", f"/api/admin/footer/items/{self.item.id}/image"),
        ]

    def test_anonymous_visitors_are_rejected_on_every_management_endpoint(self):
        client = APIClient()
        for method, url in self._urls():
            with self.subTest(url=f"{method} {url}"):
                self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_a_signed_in_customer_is_rejected_on_every_management_endpoint(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.create_user(phone="09120000000")
        )
        for method, url in self._urls():
            with self.subTest(url=f"{method} {url}"):
                self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_a_seo_admin_has_no_footer_access(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.create_user(
                phone="09120000001", is_seo_manager=True
            )
        )
        self.assertEqual(
            client.get("/api/admin/footer/sections").status_code, 403
        )

    def test_a_rejected_write_leaves_the_footer_untouched(self):
        APIClient().post(
            "/api/admin/footer/sections", {"title": "نفوذی"}, format="json"
        )
        self.assertFalse(FooterSection.objects.filter(title="نفوذی").exists())


class FooterAdminApiTests(TempMediaRootMixin, FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = get_user_model().objects.create_user(
            phone="09121234567", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    # ── بخش‌ها ──
    def test_creating_a_section(self):
        response = self.client.post(
            "/api/admin/footer/sections",
            {"title": "خدمات مشتریان"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        section = response.json()["data"]["section"]
        self.assertEqual(section["title"], "خدمات مشتریان")
        self.assertEqual(section["variant"], "column")
        self.assertEqual(section["position"], 0)
        self.assertTrue(section["isActive"])

    def test_creating_a_section_without_a_title_is_a_validation_failure(self):
        response = self.client.post(
            "/api/admin/footer/sections", {"title": ""}, format="json"
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("title", response.json()["data"]["fieldErrors"])

    def test_updating_a_section_title(self):
        section = make_section()
        response = self.client.patch(
            f"/api/admin/footer/sections/{section.id}",
            {"title": "عنوان تازه"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        section.refresh_from_db()
        self.assertEqual(section.title, "عنوان تازه")

    def test_disabling_a_section_keeps_it_in_the_management_list(self):
        section = make_section()
        self.client.patch(
            f"/api/admin/footer/sections/{section.id}",
            {"isActive": False},
            format="json",
        )
        listed = self.client.get("/api/admin/footer/sections").json()["data"]
        self.assertEqual(len(listed["sections"]), 1)
        self.assertFalse(listed["sections"][0]["isActive"])

    def test_deleting_a_section_removes_its_items_too(self):
        section = make_section()
        make_link(section)
        response = self.client.delete(f"/api/admin/footer/sections/{section.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FooterItem.objects.count(), 0)

    def test_moving_a_section_returns_the_whole_new_order(self):
        make_section(title="یک")
        second = make_section(title="دو")
        response = self.client.post(
            f"/api/admin/footer/sections/{second.id}/move",
            {"direction": "up"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()["data"]["sections"]],
            ["دو", "یک"],
        )

    def test_an_unknown_move_direction_is_rejected(self):
        section = make_section()
        response = self.client.post(
            f"/api/admin/footer/sections/{section.id}/move",
            {"direction": "sideways"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_a_missing_section_is_a_404(self):
        self.assertEqual(
            self.client.patch(
                "/api/admin/footer/sections/9999", {"title": "x"}, format="json"
            ).status_code,
            404,
        )

    # ── آیتم‌ها ──
    def test_creating_an_item_inside_a_section(self):
        section = make_section()
        response = self.client.post(
            f"/api/admin/footer/sections/{section.id}/items",
            {
                "itemType": "link",
                "label": "پرسش‌های متداول",
                "url": "/support",
                "staticPageKey": "support",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        item = response.json()["data"]["item"]
        self.assertEqual(item["label"], "پرسش‌های متداول")
        self.assertEqual(item["staticPageKey"], "support")
        self.assertEqual(item["sectionId"], section.id)

    def test_creating_an_item_with_an_unsafe_url_is_rejected(self):
        section = make_section()
        response = self.client.post(
            f"/api/admin/footer/sections/{section.id}/items",
            {"itemType": "link", "label": "بد", "url": "javascript:alert(1)"},
            format="json",
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("url", response.json()["data"]["fieldErrors"])

    def test_creating_an_item_in_a_missing_section_is_a_404(self):
        response = self.client.post(
            "/api/admin/footer/sections/9999/items",
            {"itemType": "link", "label": "x", "url": "/x"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_editing_an_item(self):
        section = make_section()
        item = make_link(section)
        response = self.client.patch(
            f"/api/admin/footer/items/{item.id}",
            {"label": "برچسب تازه", "openInNewTab": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.label, "برچسب تازه")
        self.assertTrue(item.open_in_new_tab)

    def test_deactivating_an_item_keeps_it_for_the_admin(self):
        section = make_section()
        item = make_link(section)
        self.client.patch(
            f"/api/admin/footer/items/{item.id}", {"isActive": False}, format="json"
        )
        listed = self.client.get("/api/admin/footer/sections").json()["data"]
        self.assertFalse(listed["sections"][0]["items"][0]["isActive"])

    def test_deleting_an_item(self):
        section = make_section()
        item = make_link(section)
        self.assertEqual(
            self.client.delete(f"/api/admin/footer/items/{item.id}").status_code, 200
        )
        self.assertEqual(FooterItem.objects.count(), 0)

    def test_moving_an_item_returns_the_new_order_of_its_section(self):
        section = make_section()
        make_link(section, label="الف")
        second = make_link(section, label="ب")
        response = self.client.post(
            f"/api/admin/footer/items/{second.id}/move",
            {"direction": "up"},
            format="json",
        )
        self.assertEqual(
            [item["label"] for item in response.json()["data"]["items"]],
            ["ب", "الف"],
        )

    # ── تنظیمات سراسری ──
    def test_reading_and_updating_the_global_settings(self):
        response = self.client.patch(
            "/api/admin/footer/settings",
            {
                "description": "توضیح تازه",
                "phone": "021-12345678",
                "email": "info@example.com",
                "address": "تهران",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        settings_payload = response.json()["data"]["settings"]
        self.assertEqual(settings_payload["description"], "توضیح تازه")
        self.assertEqual(settings_payload["phoneUrl"], "tel:02112345678")
        self.assertEqual(settings_payload["emailUrl"], "mailto:info@example.com")

    def test_an_invalid_settings_value_is_reported_per_field(self):
        response = self.client.patch(
            "/api/admin/footer/settings", {"email": "nope"}, format="json"
        )
        self.assertEqual(response.status_code, 422)
        self.assertIn("email", response.json()["data"]["fieldErrors"])

    # ── تصویرها ──
    def test_uploading_and_removing_the_footer_logo(self):
        response = self.client.post(
            "/api/admin/footer/settings/logo",
            {"file": make_image_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["data"]["settings"]["logo"])

        response = self.client.delete("/api/admin/footer/settings/logo")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"]["settings"]["logo"])

    def test_a_file_that_is_not_an_image_is_rejected(self):
        response = self.client.post(
            "/api/admin/footer/settings/logo",
            {"file": SimpleUploadedFile("x.png", b"not an image", "image/png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 422)

    def test_an_oversized_image_is_rejected(self):
        oversized = SimpleUploadedFile(
            "big.png", b"0" * (2 * 1024 * 1024 + 1), "image/png"
        )
        response = self.client.post(
            "/api/admin/footer/settings/logo",
            {"file": oversized},
            format="multipart",
        )
        self.assertEqual(response.status_code, 422)

    def test_an_image_item_carries_its_uploaded_file(self):
        section = make_section()
        item = FooterItem(section=section, item_type="image", image=make_image_file())
        item.save()
        response = self.client.post(
            f"/api/admin/footer/items/{item.id}/image",
            {"file": make_image_file("second.png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["data"]["item"]["image"])
