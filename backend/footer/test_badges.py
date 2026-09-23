from io import BytesIO
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from .badges import validate_badge_image
from .dto import admin_item_dto, item_dto
from .models import FooterItem, FooterSection
from .services import (
    FooterValidationError, create_item, create_section, delete_item,
    delete_section, move_item, save_trust_badge, update_item, update_section,
)
from .tests import FooterResetMixin, TempMediaRootMixin, SAFE_SVG, make_image_file

ADMIN = "/api/admin/footer/trust-badges"


def badge_file(fmt="PNG", name=None):
    buffer = BytesIO()
    Image.new("RGB", (32, 64), "white").save(buffer, format=fmt)
    return SimpleUploadedFile(name or f"badge.{fmt.lower()}", buffer.getvalue())


def make_badge(**fields):
    return save_trust_badge(**{
        "label": "نماد اعتماد الکترونیکی",
        "url": "https://trustseal.enamad.ir/?id=123&Code=example",
        "image": badge_file(), "open_in_new_tab": True, **fields,
    })


class FooterTrustBadgeTests(TempMediaRootMixin, FooterResetMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(phone="09120000111", is_staff=True)
        self.client.force_authenticate(self.admin)

    def payload(self, **fields):
        return {"label": "اینماد", "url": "https://example.com/verify", "file": badge_file(), **fields}

    def public_badges(self):
        response = self.client.get("/api/footer")
        self.assertEqual(response.status_code, 200)
        sections = [section for section in response.data["data"]["sections"] if section["variant"] == "badges"]
        return sections[0]["items"] if sections else []

    def test_creation_reuses_footer_section_and_items(self):
        first = make_badge()
        second = make_badge(label="مجوز کسب‌وکار")
        self.assertEqual(first.section_id, second.section_id)
        self.assertEqual(first.item_type, "badge")
        self.assertEqual(FooterSection.objects.filter(variant="badges").count(), 1)
        self.assertEqual((first.position, second.position), (0, 1))

    def test_create_update_image_and_metadata_in_one_request(self):
        created = self.client.post(ADMIN, self.payload(position=4, altText="نماد فروشگاه"), format="multipart")
        self.assertEqual(created.status_code, 201, created.data)
        item = created.data["data"]["item"]
        self.assertEqual(item["altText"], "نماد فروشگاه")
        self.assertEqual(item["position"], 4)
        self.assertTrue(item["isActive"])
        original = FooterItem.objects.get(pk=item["id"]).image
        with self.captureOnCommitCallbacks(execute=True):
            result = self.client.post(f'{ADMIN}/{item["id"]}', self.payload(label="مجوز جدید", position=2, file=badge_file("WEBP")), format="multipart")
            self.assertEqual(result.status_code, 200, result.data)
        updated = result.data["data"]["item"]
        self.assertEqual(updated["label"], "مجوز جدید")
        self.assertEqual(updated["position"], 2)
        self.assertTrue(updated["image"].endswith(".webp"))
        self.assertFalse(original.storage.exists(original.name))

    def test_metadata_update_keeps_image_and_alt_fallback_follows_title(self):
        item = make_badge()
        self.assertIsNone(admin_item_dto(item)["altText"])
        self.assertEqual(item_dto(item)["altText"], item.label)
        response = self.client.post(f"{ADMIN}/{item.pk}", {"label": "عنوان تازه", "url": item.url, "altText": ""}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        item.refresh_from_db()
        self.assertEqual(item_dto(item)["altText"], "عنوان تازه")
        self.assertTrue(item.image)

    def test_invalid_first_badge_does_not_leave_a_section_or_file(self):
        response = self.client.post(ADMIN, self.payload(url="javascript:alert(1)"), format="multipart")
        self.assertEqual(response.status_code, 422)
        self.assertFalse(FooterSection.objects.filter(variant="badges").exists())
        self.assertFalse(FooterItem.objects.filter(item_type="badge").exists())

    def test_invalid_replacement_rolls_back_metadata_and_preserves_original_file(self):
        item = make_badge()
        original = item.image.name
        response = self.client.post(f"{ADMIN}/{item.pk}", self.payload(label="تغییر نام", file=SimpleUploadedFile("bad.svg", b"bad")), format="multipart")
        self.assertEqual(response.status_code, 422)
        item.refresh_from_db()
        self.assertEqual(item.label, "نماد اعتماد الکترونیکی")
        self.assertEqual(item.image.name, original)
        self.assertTrue(item.image.storage.exists(original))

    def test_enable_disable_delete_use_existing_item_endpoints(self):
        item = make_badge()
        path = f"/api/admin/footer/items/{item.pk}"
        self.assertEqual(self.client.patch(path, {"isActive": False}, format="json").status_code, 200)
        self.assertEqual(self.public_badges(), [])
        self.assertEqual(self.client.patch(path, {"isActive": True}, format="json").status_code, 200)
        self.assertEqual(len(self.public_badges()), 1)
        image = item.image
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(path).status_code, 200)
        self.assertFalse(image.storage.exists(image.name))
        self.assertEqual(self.public_badges(), [])

    def test_inactive_section_hides_all_badges(self):
        item = make_badge()
        update_section(item.section, is_active=False)
        self.assertEqual(self.public_badges(), [])
        update_section(item.section, is_active=True)
        self.assertEqual(len(self.public_badges()), 1)

    def test_public_api_filters_disabled_sorts_and_omits_admin_fields(self):
        later = make_badge(position=9)
        make_badge(is_active=False, position=0)
        first = make_badge(position=2)
        self.client.force_authenticate(None)
        items = self.public_badges()
        self.assertEqual([item["id"] for item in items], [first.pk, later.pk])
        for item in items:
            self.assertNotIn("isActive", item)
            self.assertNotIn("createdAt", item)
            self.assertNotIn("embedCode", item)
            self.assertEqual(item["altText"], "نماد اعتماد الکترونیکی")

    def test_numeric_order_and_arrow_reordering(self):
        first = make_badge(position=8)
        second = make_badge(position=8)
        third = make_badge(position=10)
        response = self.client.post(f"/api/admin/footer/items/{third.pk}/move", {"direction": "up"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in self.public_badges()], [first.pk, third.pk, second.pk])
        move_item(first, "up")
        self.assertEqual(self.public_badges()[0]["id"], first.pk)

    def test_rejects_unsafe_or_malformed_links(self):
        for url in ["javascript:alert(1)", "data:text/html,test", "//evil.example", "/support", "mailto:x@example.com", "https://", "https://example.com:99999", "https://example.com\\evil", "https://user:pass@example.com", "https://example.com/%0a", "https://example.com/<script>"]:
            with self.subTest(url=url), self.assertRaises(FooterValidationError):
                make_badge(url=url)

    def test_http_and_https_custom_providers_are_supported(self):
        for url in ["http://legacy.example.com/license/1", "https://custom.example.com/license?id=1&code=abc"]:
            self.assertEqual(make_badge(url=url).url, url)

    def test_required_fields_plain_text_and_nonnegative_order(self):
        for fields in [{"label": ""}, {"label": "<script>x</script>"}, {"url": ""}, {"image": None}, {"alt_text": "<img src=x>"}, {"position": -1}]:
            with self.subTest(fields=fields), self.assertRaises(FooterValidationError):
                make_badge(**fields)
        response = self.client.post(ADMIN, self.payload(position=-1), format="multipart")
        self.assertEqual(response.status_code, 422)
        self.assertIn("position", response.data["data"]["fieldErrors"])

    def test_embed_code_is_explicitly_rejected(self):
        response = self.client.post(ADMIN, self.payload(embedCode="<script>alert(1)</script>"), format="multipart")
        self.assertEqual(response.status_code, 422)
        self.assertFalse(FooterItem.objects.filter(item_type="badge").exists())

    def test_supported_file_formats_including_safe_svg(self):
        files = [badge_file(), badge_file("JPEG", "badge.jpg"), badge_file("JPEG", "badge.jpeg"), badge_file("WEBP"), SimpleUploadedFile("badge.svg", SAFE_SVG)]
        for file in files:
            with self.subTest(name=file.name):
                response = self.client.post(ADMIN, self.payload(file=file), format="multipart")
                self.assertEqual(response.status_code, 201, response.data)

    def test_rejects_scripts_disguised_images_invalid_types_and_oversized_files(self):
        files = [
            SimpleUploadedFile("bad.png", b"<script>x</script>"),
            SimpleUploadedFile("bad.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>'),
            SimpleUploadedFile("bad.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'),
            SimpleUploadedFile("bad.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/tracker"/></svg>'),
            badge_file("PNG", "fake.jpg"), badge_file("GIF"),
            SimpleUploadedFile("large.png", b"x" * (2 * 1024 * 1024 + 1)),
            SimpleUploadedFile("large.svg", b"x" * (5 * 1024 * 1024 + 1)),
        ]
        for file in files:
            with self.subTest(name=file.name), self.assertRaises(ValidationError):
                validate_badge_image(file)

    def test_image_dimensions_are_bounded(self):
        file = make_image_file(size=(4097, 4096))
        with self.assertRaises(ValidationError):
            validate_badge_image(file)

    def test_existing_image_endpoint_cannot_bypass_badge_validation(self):
        item = make_badge()
        path = f"/api/admin/footer/items/{item.pk}/image"
        self.assertEqual(self.client.post(path, {"file": badge_file("GIF")}, format="multipart").status_code, 422)
        self.assertEqual(self.client.post(path, {"file": SimpleUploadedFile("safe.svg", SAFE_SVG)}, format="multipart").status_code, 201)
        self.assertEqual(self.client.delete(path).status_code, 422)

    def test_badges_and_regular_content_cannot_mix_or_silently_change_layout(self):
        item = make_badge()
        with self.assertRaises(FooterValidationError):
            create_item(section=item.section, item_type="text", text="text")
        with self.assertRaises(FooterValidationError):
            update_item(item, item_type="image")
        with self.assertRaises(FooterValidationError):
            update_section(item.section, variant="column")
        section = create_section(title="links")
        with self.assertRaises(FooterValidationError):
            create_item(section=section, item_type="badge", label="badge", url="https://example.com", image=badge_file())

    def test_deleting_section_cleans_badge_files(self):
        item = make_badge()
        image = item.image
        with self.captureOnCommitCallbacks(execute=True):
            delete_section(item.section)
        self.assertFalse(image.storage.exists(image.name))

    def test_badge_count_does_not_increase_public_query_count(self):
        make_badge()
        with CaptureQueriesContext(connection) as one:
            self.client.get("/api/footer")
        for index in range(5):
            make_badge(label=f"badge {index}")
        with CaptureQueriesContext(connection) as many:
            self.client.get("/api/footer")
        self.assertEqual(len(one), len(many))

    def test_changes_use_existing_footer_cache_invalidation(self):
        with patch("footer.services.schedule_footer_revalidation") as revalidate:
            first, second = make_badge(), make_badge()
            save_trust_badge(item=first, label="new")
            move_item(second, "up")
            delete_item(first)
            self.assertEqual(revalidate.call_count, 5)

    def test_write_endpoints_require_shop_admin_and_do_not_edit_regular_items(self):
        item = make_badge()
        customer = get_user_model().objects.create_user(phone="09120000112")
        seo = get_user_model().objects.create_user(phone="09120000113", is_seo_manager=True)
        for user in [None, customer, seo]:
            self.client.force_authenticate(user)
            for path in [ADMIN, f"{ADMIN}/{item.pk}"]:
                with self.subTest(user=user, path=path):
                    self.assertIn(self.client.post(path, self.payload(), format="multipart").status_code, [401, 403])
        self.client.force_authenticate(self.admin)
        section = create_section(title="text")
        regular = create_item(section=section, item_type="text", text="text")
        for pk in [regular.pk, 999999]:
            self.assertEqual(self.client.post(f"{ADMIN}/{pk}", self.payload(), format="multipart").status_code, 404)
