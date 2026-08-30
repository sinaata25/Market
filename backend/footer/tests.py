import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

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

from django.core.cache import cache

from .dto import admin_icon_dto, item_dto, public_location_dto, settings_dto
from .geocoding import GeocodingUnavailable
from .maps import is_google_maps_url, maps_directions_url, maps_search_url
from .models import FooterIcon, FooterItem, FooterSection, FooterSettings
from .services import (
    FooterValidationError,
    create_icon,
    create_item,
    create_section,
    delete_icon,
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


SAFE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    b'<circle cx="12" cy="12" r="8" fill="#467235"/></svg>'
)


def make_icon_file(name="icon.svg", data: bytes = SAFE_SVG) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, data, content_type="image/svg+xml")


def make_icon(name="ارسال") -> FooterIcon:
    return create_icon(name=name, image=make_icon_file())


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


# ───────────────────────────── موقعیت فروشگاه ───────────────────────────────

TEHRAN = {"latitude": Decimal("35.715298"), "longitude": Decimal("51.404343")}


class ShopLocationModelTests(FooterResetMixin, TestCase):
    def test_valid_coordinates_are_stored(self):
        settings_row = update_settings(**TEHRAN)
        settings_row.refresh_from_db()
        self.assertEqual(settings_row.latitude, Decimal("35.715298"))
        self.assertEqual(settings_row.longitude, Decimal("51.404343"))

    def test_latitude_outside_its_range_is_rejected(self):
        for value in (Decimal("90.000001"), Decimal("-90.000001")):
            with self.subTest(latitude=value), self.assertRaises(ValidationError):
                FooterSettings(
                    pk=1, latitude=value, longitude=Decimal("51")
                ).save()

    def test_longitude_outside_its_range_is_rejected(self):
        for value in (Decimal("180.000001"), Decimal("-180.000001")):
            with self.subTest(longitude=value), self.assertRaises(ValidationError):
                FooterSettings(
                    pk=1, latitude=Decimal("35"), longitude=value
                ).save()

    def test_the_range_boundaries_themselves_are_accepted(self):
        FooterSettings(pk=1, latitude=Decimal("-90"), longitude=Decimal("180")).save()

    def test_half_a_coordinate_pair_is_rejected(self):
        with self.assertRaises(ValidationError):
            FooterSettings(pk=1, latitude=Decimal("35.7")).save()
        with self.assertRaises(ValidationError):
            FooterSettings(pk=1, longitude=Decimal("51.4")).save()

    def test_clearing_both_coordinates_is_allowed(self):
        update_settings(**TEHRAN)
        settings_row = update_settings(latitude=None, longitude=None)
        self.assertIsNone(settings_row.latitude)
        self.assertIsNone(settings_row.longitude)

    def test_zoom_outside_its_range_is_rejected(self):
        for value in (0, 22):
            with self.subTest(zoom=value), self.assertRaises(ValidationError):
                FooterSettings(pk=1, map_zoom=value).save()

    def test_a_non_google_maps_link_is_rejected(self):
        for url in (
            "javascript:alert(1)",
            "/maps",
            "https://evil.example/maps",
            "https://google.com/search?q=x",
        ):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                FooterSettings(pk=1, maps_place_url=url).save()

    def test_google_maps_links_are_accepted(self):
        for url in (
            "https://www.google.com/maps/place/Shop",
            "https://maps.app.goo.gl/abc123",
            "https://google.de/maps?q=1,2",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_google_maps_url(url))
                self.assertEqual(
                    update_settings(maps_place_url=url).maps_place_url, url
                )

    def test_the_shop_address_reuses_the_single_footer_address_field(self):
        """نشانی فروشگاه فیلد جداگانه ندارد — همان address تنظیمات فوتر است"""
        field_names = {field.name for field in FooterSettings._meta.get_fields()}
        self.assertIn("address", field_names)
        self.assertNotIn("shop_address", field_names)


class ShopLocationUrlTests(TestCase):
    def test_the_maps_destination_is_built_from_the_saved_coordinates(self):
        url = maps_search_url(Decimal("35.715298"), Decimal("51.404343"))
        self.assertIn("query=35.715298%2C51.404343", url)
        self.assertTrue(url.startswith("https://www.google.com/maps/search/"))

    def test_the_directions_destination_is_built_from_the_saved_coordinates(self):
        url = maps_directions_url(Decimal("35.715298"), Decimal("51.404343"))
        self.assertIn("destination=35.715298%2C51.404343", url)
        self.assertTrue(url.startswith("https://www.google.com/maps/dir/"))

    def test_trailing_zeros_do_not_leak_into_the_destination(self):
        self.assertIn(
            "query=35.7%2C51", maps_search_url(Decimal("35.700000"), Decimal("51.000000"))
        )

    def test_a_whole_number_coordinate_never_becomes_scientific_notation(self):
        self.assertIn("query=35%2C50", maps_search_url(Decimal("35"), Decimal("50")))


class ShopLocationDtoTests(FooterResetMixin, TestCase):
    def test_a_configured_location_is_exposed_with_both_destinations(self):
        settings_row = update_settings(address="تهران، آزادی", **TEHRAN)
        location = public_location_dto(settings_row)
        self.assertEqual(location["address"], "تهران، آزادی")
        self.assertEqual(location["latitude"], "35.715298")
        self.assertEqual(location["zoom"], 15)
        self.assertIn("35.715298%2C51.404343", location["mapsUrl"])
        self.assertIn("35.715298%2C51.404343", location["directionsUrl"])

    def test_no_coordinates_means_no_location_block(self):
        self.assertIsNone(public_location_dto(update_settings(address="تهران")))

    def test_turning_the_map_off_hides_the_location_block(self):
        settings_row = update_settings(show_map=False, **TEHRAN)
        self.assertIsNone(public_location_dto(settings_row))

    def test_an_admin_place_link_replaces_only_the_view_destination(self):
        settings_row = update_settings(
            maps_place_url="https://maps.app.goo.gl/abc123", **TEHRAN
        )
        location = public_location_dto(settings_row)
        self.assertEqual(location["mapsUrl"], "https://maps.app.goo.gl/abc123")
        # مسیریابی هرگز به لینک دستی تکیه نمی‌کند
        self.assertIn("35.715298%2C51.404343", location["directionsUrl"])


class ShopLocationPublicApiTests(FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def _location(self):
        return self.client.get("/api/footer").json()["data"]["settings"]["location"]

    def test_the_public_footer_carries_the_shop_location(self):
        update_settings(address="تهران، آزادی", **TEHRAN)
        location = self._location()
        self.assertEqual(location["latitude"], "35.715298")
        self.assertEqual(location["longitude"], "51.404343")

    def test_the_public_footer_omits_the_location_when_the_map_is_off(self):
        update_settings(show_map=False, **TEHRAN)
        self.assertIsNone(self._location())

    def test_the_public_footer_omits_the_location_when_coordinates_are_missing(self):
        update_settings(address="تهران، آزادی")
        self.assertIsNone(self._location())

    def test_the_address_still_shows_in_the_footer_when_the_map_is_off(self):
        update_settings(address="تهران، آزادی", show_map=False)
        settings_payload = self.client.get("/api/footer").json()["data"]["settings"]
        self.assertEqual(settings_payload["address"], "تهران، آزادی")
        self.assertIsNone(settings_payload["location"])

    def test_the_location_never_exposes_management_only_fields(self):
        update_settings(**TEHRAN)
        location = self._location()
        for field in ("showMap", "mapsPlaceUrl", "updatedAt"):
            self.assertNotIn(field, location)


class ShopLocationAdminApiTests(FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user(phone="09121234567", is_staff=True)
        )

    def _patch(self, payload):
        return self.client.patch(
            "/api/admin/footer/settings", payload, format="json"
        )

    def test_saving_a_location_picked_on_the_map(self):
        response = self._patch(
            {
                "latitude": "35.715298",
                "longitude": "51.404343",
                "address": "تهران، خیابان آزادی",
                "mapZoom": 17,
            }
        )
        self.assertEqual(response.status_code, 200)
        settings_payload = response.json()["data"]["settings"]
        self.assertEqual(settings_payload["latitude"], "35.715298")
        self.assertEqual(settings_payload["mapZoom"], 17)
        self.assertIn("35.715298%2C51.404343", settings_payload["directionsUrl"])

    def test_updating_an_existing_location(self):
        self._patch({"latitude": "35.7", "longitude": "51.4"})
        response = self._patch({"latitude": "36.2", "longitude": "50.1"})
        self.assertEqual(response.status_code, 200)
        settings_row = FooterSettings.load()
        self.assertEqual(settings_row.latitude, Decimal("36.200000"))
        self.assertEqual(settings_row.longitude, Decimal("50.100000"))

    def test_an_out_of_range_latitude_is_reported_on_its_field(self):
        response = self._patch({"latitude": "120", "longitude": "51.4"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("latitude", response.json()["data"]["fieldErrors"])

    def test_an_out_of_range_longitude_is_reported_on_its_field(self):
        response = self._patch({"latitude": "35.7", "longitude": "-200"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("longitude", response.json()["data"]["fieldErrors"])

    def test_a_lone_latitude_is_rejected(self):
        response = self._patch({"latitude": "35.7"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("longitude", response.json()["data"]["fieldErrors"])

    def test_blank_coordinates_clear_the_saved_location(self):
        self._patch({"latitude": "35.7", "longitude": "51.4"})
        response = self._patch({"latitude": "", "longitude": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"]["settings"]["latitude"])

    def test_a_non_numeric_coordinate_is_rejected_before_it_reaches_the_model(self):
        self.assertEqual(self._patch({"latitude": "abc", "longitude": "1"}).status_code, 400)

    def test_toggling_the_footer_map_off_and_on(self):
        self._patch({"latitude": "35.7", "longitude": "51.4"})
        self.assertFalse(
            self._patch({"showMap": False}).json()["data"]["settings"]["showMap"]
        )
        self.assertTrue(
            self._patch({"showMap": True}).json()["data"]["settings"]["showMap"]
        )

    def test_an_out_of_range_zoom_is_rejected(self):
        self.assertEqual(self._patch({"mapZoom": 40}).status_code, 400)

    def test_a_non_google_place_link_is_rejected(self):
        response = self._patch({"mapsPlaceUrl": "https://evil.example/maps"})
        self.assertEqual(response.status_code, 422)
        self.assertIn("mapsPlaceUrl", response.json()["data"]["fieldErrors"])


class ShopLocationPermissionTests(FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def _urls(self):
        return [
            ("patch", "/api/admin/footer/settings"),
            ("get", "/api/admin/footer/geocode/search?q=tehran"),
            ("get", "/api/admin/footer/geocode/reverse?lat=35.7&lng=51.4"),
        ]

    def test_anonymous_visitors_cannot_read_or_write_shop_location_tools(self):
        client = APIClient()
        for method, url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_a_customer_cannot_reach_the_geocoding_proxy(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.create_user(phone="09120000000")
        )
        for method, url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_a_customer_cannot_move_the_shop_by_crafting_a_payload(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.create_user(phone="09120000001")
        )
        client.patch(
            "/api/admin/footer/settings",
            {"latitude": "1", "longitude": "1"},
            format="json",
        )
        self.assertIsNone(FooterSettings.load().latitude)


class GeocodingProxyTests(FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user(phone="09121234567", is_staff=True)
        )

    def test_searching_an_address_returns_usable_coordinates(self):
        payload = [
            {"display_name": "تهران، آزادی", "lat": "35.7152981", "lon": "51.4043433"},
            {"display_name": "بدون مختصات", "lat": "not-a-number", "lon": "51.4"},
        ]
        with patch("footer.geocoding._request", return_value=payload):
            response = self.client.get("/api/admin/footer/geocode/search?q=آزادی")
        self.assertEqual(response.status_code, 200)
        results = response.json()["data"]["results"]
        # ردیف بی‌مختصات بی‌سروصدا کنار گذاشته می‌شود، نه اینکه پاسخ را بشکند
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["latitude"], "35.715298")

    def test_an_empty_search_term_is_rejected(self):
        self.assertEqual(
            self.client.get("/api/admin/footer/geocode/search?q=  ").status_code, 422
        )

    def test_reverse_lookup_returns_a_human_readable_address(self):
        with patch("footer.geocoding._request", return_value={"display_name": "تهران"}):
            response = self.client.get(
                "/api/admin/footer/geocode/reverse?lat=35.7&lng=51.4"
            )
        self.assertEqual(response.json()["data"]["address"], "تهران")

    def test_reverse_lookup_rejects_coordinates_outside_the_world(self):
        for query in ("lat=120&lng=51", "lat=35&lng=200", "lat=x&lng=1", "lat=35"):
            with self.subTest(query=query):
                self.assertEqual(
                    self.client.get(
                        f"/api/admin/footer/geocode/reverse?{query}"
                    ).status_code,
                    422,
                )

    def test_a_provider_outage_is_a_controlled_failure_not_a_500(self):
        with patch("footer.geocoding._request", side_effect=GeocodingUnavailable):
            search_response = self.client.get(
                "/api/admin/footer/geocode/search?q=tehran"
            )
            reverse_response = self.client.get(
                "/api/admin/footer/geocode/reverse?lat=35.7&lng=51.4"
            )
        self.assertEqual(search_response.status_code, 503)
        self.assertEqual(reverse_response.status_code, 503)
        self.assertFalse(search_response.json()["ok"])


class ShopLocationCacheTests(FooterResetMixin, TestCase):
    """فوتر روی هر صفحه کش می‌شود؛ تغییر موقعیت باید کش را باطل کند"""

    def test_saving_a_location_schedules_a_footer_cache_revalidation(self):
        with patch("footer.services.schedule_footer_revalidation") as scheduled:
            update_settings(**TEHRAN)
        self.assertTrue(scheduled.called)

    def test_toggling_the_map_schedules_a_footer_cache_revalidation(self):
        update_settings(**TEHRAN)
        with patch("footer.services.schedule_footer_revalidation") as scheduled:
            update_settings(show_map=False)
        self.assertTrue(scheduled.called)


# ───────────────────────────── کتابخانه‌ی آیکن‌ها ────────────────────────────


class FooterIconModelTests(TempMediaRootMixin, FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        FooterIcon.objects.all().delete()

    def test_an_icon_needs_a_file(self):
        with self.assertRaises(ValidationError):
            FooterIcon(name="بدون فایل").save()

    def test_icon_names_are_unique(self):
        make_icon("ارسال")
        with self.assertRaises(FooterValidationError):
            make_icon("ارسال")

    def test_html_in_an_icon_name_is_rejected(self):
        with self.assertRaises(FooterValidationError):
            create_icon(name="<b>ارسال</b>", image=make_icon_file())

    def test_an_unsafe_svg_is_rejected(self):
        unsafe = (
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            b'<script>alert(1)</script></svg>'
        )
        with self.assertRaises(FooterValidationError):
            create_icon(name="خطرناک", image=make_icon_file("bad.svg", unsafe))

    def test_a_non_icon_file_type_is_rejected(self):
        with self.assertRaises(FooterValidationError):
            create_icon(
                name="جیپگ",
                image=SimpleUploadedFile("x.jpg", b"nope", "image/jpeg"),
            )

    def test_a_png_icon_is_accepted(self):
        icon = create_icon(name="پی‌ان‌جی", image=make_image_file("icon.png"))
        self.assertTrue(icon.image)

    def test_deleting_an_icon_leaves_its_items_without_one_not_broken(self):
        icon = make_icon()
        section = make_section()
        item = make_link(section, icon_image=icon)
        delete_icon(icon)
        item.refresh_from_db()
        self.assertIsNone(item.icon_image_id)
        self.assertTrue(FooterItem.objects.filter(pk=item.pk).exists())

    def test_deleting_an_icon_clears_it_from_the_settings_rows(self):
        icon = make_icon()
        update_settings(address_icon=icon, phone_icon=icon)
        delete_icon(icon)
        settings_row = FooterSettings.load()
        self.assertIsNone(settings_row.address_icon_id)
        self.assertIsNone(settings_row.phone_icon_id)

    def test_an_icon_is_rejected_on_an_item_type_that_has_no_icon(self):
        icon = make_icon()
        section = make_section()
        with self.assertRaises(ValidationError):
            FooterItem(
                section=section,
                item_type="image",
                image=make_image_file(),
                icon_image=icon,
            ).save()

    def test_switching_item_type_drops_an_icon_the_new_type_cannot_use(self):
        icon = make_icon()
        section = make_section()
        item = make_link(section, icon_image=icon)
        update_item(item, item_type="image", image=make_image_file())
        item.refresh_from_db()
        self.assertIsNone(item.icon_image_id)

    def test_the_usage_count_reports_how_many_items_use_the_icon(self):
        icon = make_icon()
        section = make_section()
        make_link(section, label="یک", icon_image=icon)
        make_link(section, label="دو", icon_image=icon)
        self.assertEqual(admin_icon_dto(icon)["usageCount"], 2)


class FooterIconPublicApiTests(TempMediaRootMixin, FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        FooterIcon.objects.all().delete()
        self.client = APIClient()

    def test_an_item_exposes_its_icon_file_to_the_storefront(self):
        icon = make_icon()
        section = make_section()
        make_link(section, icon_image=icon)
        item = self.client.get("/api/footer").json()["data"]["sections"][0]["items"][0]
        self.assertTrue(item["iconImage"].endswith(".svg"))

    def test_the_emoji_remains_only_as_a_fallback(self):
        section = make_section()
        make_link(section, icon="🚚")
        item = self.client.get("/api/footer").json()["data"]["sections"][0]["items"][0]
        self.assertIsNone(item["iconImage"])
        self.assertEqual(item["icon"], "🚚")

    def test_the_contact_row_icons_come_from_settings_not_the_component(self):
        icon = make_icon()
        update_settings(
            address="تهران",
            phone="021-12345678",
            email="a@b.com",
            address_icon=icon,
            phone_icon=icon,
            email_icon=icon,
        )
        settings_payload = self.client.get("/api/footer").json()["data"]["settings"]
        for key in ("addressIcon", "phoneIcon", "emailIcon"):
            self.assertTrue(settings_payload[key].endswith(".svg"))

    def test_the_map_row_reuses_the_address_icon(self):
        icon = make_icon()
        update_settings(
            address_icon=icon,
            latitude=Decimal("35.7"),
            longitude=Decimal("51.4"),
        )
        location = self.client.get("/api/footer").json()["data"]["settings"]["location"]
        self.assertTrue(location["icon"].endswith(".svg"))

    def test_missing_icons_are_null_rather_than_breaking_the_footer(self):
        update_settings(address="تهران", phone="021-12345678")
        settings_payload = self.client.get("/api/footer").json()["data"]["settings"]
        self.assertIsNone(settings_payload["addressIcon"])
        self.assertIsNone(settings_payload["phoneIcon"])

    def test_icons_do_not_add_a_query_per_item(self):
        icon = make_icon()
        FooterSettings.load()
        section = make_section()
        make_link(section, icon_image=icon)
        with CaptureQueriesContext(connection) as small:
            self.client.get("/api/footer")
        for index in range(5):
            make_link(section, label=f"پیوند {index}", icon_image=icon)
        with CaptureQueriesContext(connection) as large:
            self.client.get("/api/footer")
        self.assertEqual(len(large), len(small))


class FooterIconAdminApiTests(TempMediaRootMixin, FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        FooterIcon.objects.all().delete()
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_user(phone="09121234567", is_staff=True)
        )

    def test_creating_an_icon_with_its_file(self):
        response = self.client.post(
            "/api/admin/footer/icons",
            {"name": "ارسال", "file": make_icon_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        icon = response.json()["data"]["icon"]
        self.assertEqual(icon["name"], "ارسال")
        self.assertTrue(icon["image"])
        self.assertEqual(icon["usageCount"], 0)

    def test_creating_an_icon_without_a_file_is_rejected(self):
        response = self.client.post(
            "/api/admin/footer/icons", {"name": "بدون فایل"}, format="multipart"
        )
        self.assertEqual(response.status_code, 422)

    def test_creating_an_icon_with_an_unsafe_svg_is_rejected(self):
        unsafe = (
            b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
            b"</svg>"
        )
        response = self.client.post(
            "/api/admin/footer/icons",
            {"name": "خطرناک", "file": make_icon_file("bad.svg", unsafe)},
            format="multipart",
        )
        self.assertEqual(response.status_code, 422)
        self.assertFalse(FooterIcon.objects.exists())

    def test_renaming_an_icon(self):
        icon = make_icon()
        response = self.client.patch(
            f"/api/admin/footer/icons/{icon.id}", {"name": "نام تازه"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        icon.refresh_from_db()
        self.assertEqual(icon.name, "نام تازه")

    def test_replacing_an_icon_file_updates_every_place_that_uses_it(self):
        icon = make_icon()
        section = make_section()
        item = make_link(section, icon_image=icon)
        original = icon.image.name

        response = self.client.post(
            f"/api/admin/footer/icons/{icon.id}/image",
            {"file": make_icon_file("replacement.svg")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        item.refresh_from_db()
        self.assertNotEqual(item.icon_image.image.name, original)

    def test_deleting_an_icon(self):
        icon = make_icon()
        self.assertEqual(
            self.client.delete(f"/api/admin/footer/icons/{icon.id}").status_code, 200
        )
        self.assertFalse(FooterIcon.objects.exists())

    def test_a_missing_icon_is_a_404(self):
        self.assertEqual(
            self.client.patch(
                "/api/admin/footer/icons/9999", {"name": "x"}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete("/api/admin/footer/icons/9999").status_code, 404
        )

    def test_assigning_an_icon_to_an_item(self):
        icon = make_icon()
        section = make_section()
        response = self.client.post(
            f"/api/admin/footer/sections/{section.id}/items",
            {"itemType": "link", "label": "پرسش‌ها", "url": "/support", "iconId": icon.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["item"]["iconId"], icon.id)

    def test_clearing_an_items_icon(self):
        icon = make_icon()
        section = make_section()
        item = make_link(section, icon_image=icon)
        response = self.client.patch(
            f"/api/admin/footer/items/{item.id}", {"iconId": None}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertIsNone(item.icon_image_id)

    def test_an_unknown_icon_id_is_rejected(self):
        section = make_section()
        response = self.client.post(
            f"/api/admin/footer/sections/{section.id}/items",
            {"itemType": "link", "label": "x", "url": "/x", "iconId": 9999},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_assigning_the_contact_icons_from_settings(self):
        icon = make_icon()
        response = self.client.patch(
            "/api/admin/footer/settings",
            {
                "addressIconId": icon.id,
                "phoneIconId": icon.id,
                "emailIconId": icon.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        settings_payload = response.json()["data"]["settings"]
        self.assertEqual(settings_payload["addressIconId"], icon.id)
        self.assertEqual(settings_payload["phoneIconId"], icon.id)

    def test_an_unknown_settings_icon_id_is_rejected(self):
        self.assertEqual(
            self.client.patch(
                "/api/admin/footer/settings", {"phoneIconId": 9999}, format="json"
            ).status_code,
            400,
        )


class FooterIconPermissionTests(TempMediaRootMixin, FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        FooterIcon.objects.all().delete()
        self.icon = make_icon()

    def _urls(self):
        return [
            ("get", "/api/admin/footer/icons"),
            ("post", "/api/admin/footer/icons"),
            ("patch", f"/api/admin/footer/icons/{self.icon.id}"),
            ("delete", f"/api/admin/footer/icons/{self.icon.id}"),
            ("post", f"/api/admin/footer/icons/{self.icon.id}/image"),
        ]

    def test_anonymous_visitors_cannot_touch_the_icon_library(self):
        client = APIClient()
        for method, url in self._urls():
            with self.subTest(url=f"{method} {url}"):
                self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_a_customer_cannot_touch_the_icon_library(self):
        client = APIClient()
        client.force_authenticate(
            get_user_model().objects.create_user(phone="09120000000")
        )
        for method, url in self._urls():
            with self.subTest(url=f"{method} {url}"):
                self.assertEqual(getattr(client, method)(url).status_code, 403)

    def test_a_rejected_delete_leaves_the_icon_in_place(self):
        APIClient().delete(f"/api/admin/footer/icons/{self.icon.id}")
        self.assertTrue(FooterIcon.objects.filter(pk=self.icon.pk).exists())
