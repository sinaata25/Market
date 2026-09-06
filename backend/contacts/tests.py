import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from footer.models import FooterIcon
from footer.services import delete_icon, update_icon
from .dto import button_dto
from .models import FloatingContactButton
from .services import create_button, delete_button, move_button, update_button
from .validation import normalize_phone, safe_destination, validate_contact_icon

PUBLIC = "/api/site-settings/floating-contact-buttons"
ADMIN = "/api/admin/floating-contact-buttons"
SAFE_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/></svg>'


def image_file(fmt="PNG", name=None):
    buffer = BytesIO()
    Image.new("RGB", (16, 16), "green").save(buffer, format=fmt)
    return SimpleUploadedFile(name or f"icon.{fmt.lower()}", buffer.getvalue())


def make_button(**fields):
    return create_button(**{"title": "تماس", "platform": "phone", "phone_number": "+98 (912) 345-6789", **fields})


class ContactModelTests(TestCase):
    def test_creates_updates_and_disables(self):
        button = make_button()
        button = update_button(button, platform="telegram", username="@store", title="تلگرام")
        self.assertEqual(button.destination, "https://t.me/store")
        update_button(button, is_active=False)
        button.refresh_from_db()
        self.assertFalse(button.is_active)

    def test_whatsapp_phone_normalization(self):
        for number in ["+98 (912) 345-6789", "0098 912 345 6789", "۰۹۱۲۳۴۵۶۷۸۹", "٠٩١٢٣٤٥٦٧٨٩", "989123456789"]:
            with self.subTest(number=number):
                self.assertEqual(make_button(platform="whatsapp", phone_number=number).destination, "https://wa.me/989123456789")

    def test_international_phone_numbers_are_not_assumed_iranian(self):
        self.assertEqual(normalize_phone("+44 (7700) 900-123", whatsapp=True), "447700900123")

    def test_phone_and_sms_preserve_local_or_international_numbers(self):
        for platform, prefix in [("phone", "tel:"), ("sms", "sms:")]:
            self.assertEqual(make_button(platform=platform).destination, prefix + "+989123456789")
            self.assertEqual(make_button(platform=platform, phone_number="۰۹۱۲ ۳۴۵ ۶۷۸۹").destination, prefix + "09123456789")

    def test_username_presets(self):
        for platform, base in [
            ("telegram", "https://t.me/"), ("instagram", "https://instagram.com/"),
            ("bale", "https://ble.ir/"), ("eitaa", "https://eitaa.com/"),
            ("rubika", "https://rubika.ir/"), ("linkedin", "https://www.linkedin.com/in/"),
        ]:
            with self.subTest(platform=platform):
                self.assertEqual(make_button(platform=platform, username="@my_store").destination, base + "my_store")

    def test_full_url_in_username_and_explicit_url_override(self):
        button = make_button(platform="telegram", username="https://t.me/store")
        self.assertEqual(button.destination, "https://t.me/store")
        button = update_button(button, url="https://example.com/contact?from=chat")
        self.assertEqual(button.destination, "https://example.com/contact?from=chat")

    def test_arbitrary_platform_names_do_not_require_schema_changes(self):
        button = make_button(platform="future-platform", url="https://example.com")
        self.assertEqual(button.destination, "https://example.com")

    def test_email_destination(self):
        self.assertEqual(make_button(platform="email", email="sales+shop@example.com").destination, "mailto:sales+shop@example.com")

    def test_url_override_allows_omitting_platform_fields(self):
        for platform in ["phone", "sms", "whatsapp", "telegram", "instagram", "email", "custom"]:
            with self.subTest(platform=platform):
                button = make_button(platform=platform, phone_number="", url="https://example.com")
                self.assertEqual(button.destination, "https://example.com")

    def test_missing_or_invalid_fields_cannot_be_saved(self):
        cases = [
            {"title": " "}, {"title": "<script>x</script>"}, {"platform": "Bad platform"},
            {"platform": "custom"}, {"phone_number": ""}, {"phone_number": "123"},
            {"phone_number": "+98 (912 3456789"}, {"phone_number": "abc09123456789"},
            {"platform": "whatsapp", "phone_number": "021 12345678"},
            {"platform": "email", "email": "bad@"}, {"platform": "telegram", "username": ""},
            {"platform": "instagram", "username": "../evil"},
            {"platform": "telegram", "username": "store?x=y"},
            {"display_order": -1}, {"position": "top"}, {"icon_name": "unknown"},
            {"tooltip_text": "<img src=x>"},
        ]
        for fields in cases:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                make_button(**fields)

    def test_unsafe_and_malformed_urls_are_rejected(self):
        for url in [
            "javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,test", "file:///tmp/test",
            "//evil.example", "https://", "https://a@example.com", "https://example.com\\evil",
            "https://example.com/%0aHeader", "https://example.com/\n", "mailto:bad@",
            "mailto:me@example.com?bcc=other@example.com", "tel:123", "sms:+989123456789?body=x",
            "https://[broken", "https://example.com:99999/", "https://example.com/<script>",
        ]:
            with self.subTest(url=url), self.assertRaises(ValidationError):
                safe_destination(url)

    def test_appropriate_custom_schemes(self):
        for value, expected in [
            ("https://example.com/a?x=1&y=2", "https://example.com/a?x=1&y=2"),
            ("http://example.com", "http://example.com"),
            ("tel:+98 (912) 345-6789", "tel:+989123456789"),
            ("sms:0912-345-6789", "sms:09123456789"),
            ("mailto:hello@example.com", "mailto:hello@example.com"),
        ]:
            with self.subTest(value=value):
                self.assertEqual(safe_destination(value), expected)

    def test_ordering_and_moves_work_with_equal_display_orders(self):
        first = make_button(display_order=7)
        left = make_button(position="bottom-left", display_order=7)
        last = make_button(display_order=7)
        move_button(last, "up")
        self.assertEqual(list(FloatingContactButton.objects.values_list("id", flat=True)), [last.id, left.id, first.id])
        move_button(last, "up")  # Boundary is a no-op.
        self.assertEqual(list(FloatingContactButton.objects.filter(position="bottom-right").values_list("id", flat=True)), [last.id, first.id])

    def test_changes_use_existing_cache_revalidation(self):
        with patch("contacts.services.schedule_footer_revalidation") as schedule:
            first = make_button()
            second = make_button()
            update_button(first, title="new")
            move_button(second, "up")
            delete_button(first)
            self.assertEqual(schedule.call_count, 5)


class ContactApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(phone="09120000001", is_staff=True)
        self.client.force_authenticate(self.admin)

    def test_admin_create_edit_disable_delete(self):
        response = self.client.post(ADMIN, {"title": "واتساپ", "platform": "whatsapp", "phoneNumber": "09123456789"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        button = response.data["data"]["button"]
        self.assertEqual(button["url"], "https://wa.me/989123456789")
        detail = f'{ADMIN}/{button["id"]}'
        response = self.client.patch(detail, {"platform": "telegram", "username": "@store", "position": "bottom-left", "displayOrder": 3}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["data"]["button"]["url"], "https://t.me/store")
        self.assertEqual(self.client.patch(detail, {"isActive": False}, format="json").status_code, 200)
        self.assertEqual(self.client.get(PUBLIC).data["data"]["buttons"], [])
        self.assertEqual(self.client.delete(detail).status_code, 200)
        self.assertFalse(FloatingContactButton.objects.exists())

    def test_empty_public_configuration(self):
        self.client.force_authenticate(None)
        response = self.client.get(PUBLIC)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"ok": True, "data": {"buttons": []}})

    def test_public_api_only_exposes_active_render_data_in_order(self):
        last = make_button(display_order=10)
        make_button(is_active=False)
        first = make_button(display_order=0)
        self.client.force_authenticate(None)
        with self.assertNumQueries(1):
            response = self.client.get(PUBLIC)
        buttons = response.data["data"]["buttons"]
        self.assertEqual([row["id"] for row in buttons], [first.id, last.id])
        self.assertEqual(set(buttons[0]), {"id", "title", "platform", "url", "icon", "iconName", "tooltipText", "openInNewTab", "position", "displayOrder"})

    def test_admin_lists_inactive_buttons_and_platform_suggestions(self):
        make_button(is_active=False)
        data = self.client.get(ADMIN).data["data"]
        self.assertEqual(len(data["buttons"]), 1)
        self.assertFalse(data["buttons"][0]["isActive"])
        self.assertIn("custom", [item["value"] for item in data["platforms"]])

    def test_custom_platform_and_url_override(self):
        response = self.client.post(ADMIN, {"title": "سرویس جدید", "platform": "my-service", "url": "https://example.com", "iconName": "chat"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["data"]["button"]["iconName"], "chat")

    def test_validation_errors_are_field_addressable(self):
        for payload, key in [
            ({"platform": "whatsapp"}, "phoneNumber"),
            ({"platform": "custom", "url": "javascript:alert(1)"}, "url"),
            ({"platform": "email", "email": "bad"}, "email"),
            ({"platform": "phone", "displayOrder": -1}, "displayOrder"),
            ({"platform": "phone", "iconId": 999999}, "iconId"),
        ]:
            with self.subTest(payload=payload):
                response = self.client.post(ADMIN, {"title": "تماس", **payload}, format="json")
                self.assertEqual(response.status_code, 422, response.data)
                self.assertIn(key, response.data["data"]["fieldErrors"])

    def test_partial_update_uses_existing_values_and_invalid_changes_roll_back(self):
        button = make_button()
        detail = f"{ADMIN}/{button.pk}"
        self.assertEqual(self.client.patch(detail, {"tooltipText": "تماس با ما"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(detail, {"phoneNumber": ""}, format="json").status_code, 422)
        button.refresh_from_db()
        self.assertEqual(button.destination, "tel:+989123456789")

    def test_move_endpoint(self):
        first, second = make_button(), make_button()
        response = self.client.post(f"{ADMIN}/{second.pk}/move", {"direction": "up"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["data"]["buttons"]], [second.pk, first.pk])

    def test_all_admin_endpoints_require_shop_admin(self):
        button = make_button()
        customer = get_user_model().objects.create_user(phone="09120000002")
        seo = get_user_model().objects.create_user(phone="09120000003", is_seo_manager=True)
        for user in [None, customer, seo]:
            self.client.force_authenticate(user)
            for method, path in [("get", ADMIN), ("post", ADMIN), ("patch", f"{ADMIN}/{button.pk}"), ("delete", f"{ADMIN}/{button.pk}"), ("post", f"{ADMIN}/{button.pk}/move"), ("post", f"{ADMIN}/{button.pk}/icon"), ("delete", f"{ADMIN}/{button.pk}/icon")]:
                with self.subTest(user=user, method=method, path=path):
                    self.assertIn(getattr(self.client, method)(path, {}, format="json").status_code, [401, 403])

    def test_missing_buttons_return_404(self):
        for method, suffix in [("patch", ""), ("delete", ""), ("post", "/move"), ("post", "/icon"), ("delete", "/icon")]:
            self.assertEqual(getattr(self.client, method)(f"{ADMIN}/999999{suffix}", {}, format="json").status_code, 404)


class ContactIconTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_root = tempfile.mkdtemp(prefix="contact-test-media-")
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user(phone="09120000004", is_staff=True))

    def test_upload_all_supported_formats(self):
        button = make_button()
        files = [image_file(), image_file("JPEG", "icon.jpg"), image_file("WEBP"), SimpleUploadedFile("icon.svg", SAFE_SVG)]
        for file in files:
            with self.subTest(file=file.name), self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(f"{ADMIN}/{button.pk}/icon", {"file": file}, format="multipart")
                self.assertEqual(response.status_code, 201, response.data)
                self.assertTrue(response.data["data"]["button"]["icon"].startswith("/media/contacts/icons/"))

    def test_rejects_unsafe_svg_disguised_images_oversize_and_unknown_formats(self):
        files = [
            SimpleUploadedFile("bad.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
            SimpleUploadedFile("bad.svg", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'),
            SimpleUploadedFile("bad.png", b"<script>alert(1)</script>"),
            image_file("PNG", "fake.jpg"), image_file("GIF"),
            SimpleUploadedFile("large.png", b"x" * (5 * 1024 * 1024 + 1)),
            SimpleUploadedFile("large.webp", b"x" * (2 * 1024 * 1024 + 1)),
        ]
        for file in files:
            with self.subTest(file=file.name), self.assertRaises(ValidationError):
                validate_contact_icon(file)

    def test_uploaded_icon_overrides_library_and_default(self):
        library = FooterIcon.objects.create(name="مشترک", image=SimpleUploadedFile("shared.svg", SAFE_SVG))
        button = make_button(library_icon=library, icon_name="chat")
        self.assertEqual(button_dto(button)["icon"], library.image.url)
        button = update_button(button, icon=image_file())
        self.assertEqual(button_dto(button)["icon"], button.icon.url)
        button = update_button(button, icon="")
        self.assertEqual(button_dto(button)["icon"], library.image.url)
        delete_icon(library)
        button.refresh_from_db()
        self.assertIsNone(button_dto(button)["icon"])
        self.assertEqual(button_dto(button)["iconName"], "chat")

    def test_shared_icon_replacement_invalidates_the_shared_cache_tag(self):
        library = FooterIcon.objects.create(name="مشترک", image=SimpleUploadedFile("shared.svg", SAFE_SVG))
        button = make_button(library_icon=library)
        with patch("footer.services.schedule_footer_revalidation") as schedule:
            update_icon(library, image=image_file())
            schedule.assert_called_once()
        button.refresh_from_db()
        self.assertEqual(button_dto(button)["icon"], library.image.url)

    def test_replaced_removed_and_deleted_files_clean_up_after_commit(self):
        button = make_button(icon=image_file())
        old_name, storage = button.icon.name, button.icon.storage
        with self.captureOnCommitCallbacks(execute=True):
            button = update_button(button, icon=image_file())
            self.assertTrue(storage.exists(old_name))
        self.assertFalse(storage.exists(old_name))
        name = button.icon.name
        with self.captureOnCommitCallbacks(execute=True):
            delete_button(button)
        self.assertFalse(storage.exists(name))

    def test_upload_errors_preserve_previous_icon(self):
        button = make_button(icon=image_file())
        path = f"{ADMIN}/{button.pk}/icon"
        for payload in [{}, {"file": SimpleUploadedFile("bad.svg", b"bad")}]:
            response = self.client.post(path, payload, format="multipart")
            self.assertEqual(response.status_code, 422)
        self.assertEqual(FloatingContactButton.objects.get(pk=button.pk).icon.name, button.icon.name)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(path).status_code, 200)
        button.refresh_from_db()
        self.assertFalse(button.icon)
