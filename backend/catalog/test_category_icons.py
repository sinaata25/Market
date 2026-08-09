import os
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from seo.services import all_pages

from .admin import CategoryAdmin
from .models import Category, Product
from .validators import MAX_CATEGORY_ICON_SIZE


SAFE_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <defs>
    <linearGradient id="paint">
      <stop offset="0" stop-color="#15803d" />
      <stop offset="1" stop-color="#22c55e" />
    </linearGradient>
  </defs>
  <path fill="url(#paint)" d="M2 12 L12 2 L22 12 L12 22 Z" />
</svg>"""


def png_upload(
    name: str = "category.png",
    *,
    size: tuple[int, int] = (32, 32),
    trailing: bytes = b"",
) -> SimpleUploadedFile:
    output = BytesIO()
    Image.new("RGBA", size, "#16a34a").save(output, format="PNG")
    return SimpleUploadedFile(
        name,
        output.getvalue() + trailing,
        content_type="image/png",
    )


def svg_upload(
    content: bytes = SAFE_SVG,
    name: str = "category.svg",
) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="image/svg+xml")


class TemporaryMediaTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.media_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        settings_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)


class CategoryIconValidationTests(TemporaryMediaTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def assert_invalid_icon(self, icon: SimpleUploadedFile):
        category = Category(slug="invalid-icon", title="آیکن نامعتبر", icon=icon)
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_category_without_icon_uses_current_public_contract(self):
        category = Category.objects.create(
            slug="garden-tools",
            title="ابزار باغبانی",
        )
        child = Category.objects.create(slug="shovels", title="بیل")
        child.parents.add(category)

        response = self.client.get("/api/categories")

        self.assertEqual(response.status_code, 200)
        item = response.data["data"]["categories"][0]
        self.assertEqual(
            set(item), {"slug", "title", "icon", "sub", "isTopLevel"}
        )
        self.assertIsNone(item["icon"])
        self.assertEqual(item["sub"], [{"slug": "shovels", "title": "بیل"}])
        self.assertEqual(item["isTopLevel"], True)
        self.assertEqual(category.icon.name, "")

    def test_valid_png_is_stored_and_returned_as_media_url(self):
        category = Category(
            slug="garden-tools",
            title="ابزار باغبانی",
            icon=png_upload(),
        )
        category.full_clean()
        category.save()

        response = self.client.get("/api/categories")

        self.assertTrue(category.icon.name.startswith("categories/icons/"))
        self.assertTrue(os.path.exists(category.icon.path))
        self.assertEqual(
            response.data["data"]["categories"][0]["icon"],
            category.icon.url,
        )
        self.assertTrue(category.icon.url.startswith("/media/categories/icons/"))

    def test_valid_safe_svg_is_stored(self):
        category = Category(
            slug="sprayers",
            title="سمپاش‌ها",
            icon=svg_upload(),
        )
        category.full_clean()
        category.save()

        self.assertTrue(category.icon.name.endswith(".svg"))
        with category.icon.open("rb") as stored_icon:
            self.assertEqual(stored_icon.read(), SAFE_SVG)

    def test_unsupported_extensions_are_rejected(self):
        for name in ("category.jpg", "category.webp", "category.txt"):
            with self.subTest(name=name):
                self.assert_invalid_icon(
                    SimpleUploadedFile(name, b"not an allowed icon")
                )

    def test_actual_content_must_match_the_extension(self):
        mismatched_icons = (
            svg_upload(name="category.png"),
            png_upload(name="category.svg"),
            SimpleUploadedFile("category.png", b"plain text", "image/png"),
        )
        for icon in mismatched_icons:
            with self.subTest(name=icon.name):
                self.assert_invalid_icon(icon)

    def test_png_with_trailing_payload_is_rejected(self):
        self.assert_invalid_icon(png_upload(trailing=b"unexpected payload"))

    def test_excessive_png_dimensions_are_rejected(self):
        self.assert_invalid_icon(png_upload(size=(4097, 1)))

    def test_oversized_file_is_rejected(self):
        self.assert_invalid_icon(
            SimpleUploadedFile(
                "category.svg",
                b"x" * (MAX_CATEGORY_ICON_SIZE + 1),
                "image/svg+xml",
            )
        )

    def test_active_or_external_svg_content_is_rejected(self):
        unsafe_documents = {
            "script": b'<svg xmlns="http://www.w3.org/2000/svg"><script /></svg>',
            "event": b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)" />',
            "foreign-object": b'<svg xmlns="http://www.w3.org/2000/svg"><foreignObject /></svg>',
            "style-element": b'<svg xmlns="http://www.w3.org/2000/svg"><style>@import url(https://example.com/x)</style></svg>',
            "style-attribute": b'<svg xmlns="http://www.w3.org/2000/svg"><path style="fill:red" d="M0 0" /></svg>',
            "external-url": b'<svg xmlns="http://www.w3.org/2000/svg"><path fill="url(https://example.com/x)" d="M0 0" /></svg>',
            "css-escaped-url": b'<svg xmlns="http://www.w3.org/2000/svg"><path fill="u\\72l(//example.com/x)" d="M0 0" /></svg>',
            "css-image-set": b'<svg xmlns="http://www.w3.org/2000/svg" mask="image-set(\'//example.com/x\' 1x)" />',
            "embedded-image": b'<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,AA" /></svg>',
            "use-link": b'<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.com/x" /></svg>',
            "doctype-entity": b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg"><title>&xxe;</title></svg>',
            "processing-instruction": b'<?xml-stylesheet href="https://example.com/x.css"?><svg xmlns="http://www.w3.org/2000/svg" />',
            "foreign-namespace": b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:x="https://example.com"><x:node /></svg>',
        }
        for case, content in unsafe_documents.items():
            with self.subTest(case=case):
                self.assert_invalid_icon(svg_upload(content))

    def test_category_seo_title_no_longer_depends_on_a_glyph(self):
        category = Category.objects.create(slug="tools", title="ابزار")

        page = next(
            page
            for page in all_pages()
            if page["pageType"] == "category" and page["objectKey"] == category.slug
        )

        self.assertEqual(page["title"], category.title)


class CategoryAdminIconTests(TemporaryMediaTestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_superuser(
            phone="09121234567",
            password="admin-test-password",
        )
        self.client.force_login(self.user)
        self.model_admin = CategoryAdmin(Category, admin.site)
        self.request = RequestFactory().post("/")
        self.request.user = self.user

    def create_category(self, *, slug="tools", title="ابزار", icon=None):
        category = Category(slug=slug, title=title, icon=icon or "")
        category.full_clean()
        category.save()
        return category

    def change_payload(self, category, **extra):
        return {
            "slug": category.slug,
            "title": category.title,
            "_save": "Save",
            **extra,
        }

    def test_admin_form_has_icon_and_no_legacy_field(self):
        form_class = self.model_admin.get_form(self.request)

        self.assertEqual(
            set(form_class.base_fields),
            {"slug", "title", "is_active", "icon", "parents"},
        )

    def test_admin_preview_uses_an_external_image_and_handles_no_icon(self):
        blank_category = self.create_category()
        category = self.create_category(
            slug="preview",
            title="پیش‌نمایش",
            icon=svg_upload(),
        )

        preview = str(self.model_admin.icon_preview(category))

        self.assertIn("<img", preview)
        self.assertIn(category.icon.url, preview)
        self.assertNotIn("<svg", preview)
        self.assertEqual(self.model_admin.icon_preview(blank_category), "—")

    def test_admin_form_rejects_cycles_and_parent_delete_is_disabled(self):
        parent = self.create_category(slug="parent", title="والد")
        child = self.create_category(slug="child", title="فرزند")
        child.parents.add(parent)

        response = self.client.post(
            reverse("admin:catalog_category_change", args=[parent.id]),
            self.change_payload(parent, parents=[child.id]),
        )

        parent.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(parent.parents.exists())
        self.assertContains(response, "چرخه")
        self.assertFalse(self.model_admin.has_delete_permission(self.request, parent))

    def test_admin_can_create_categories_with_png_svg_or_no_icon(self):
        cases = (
            ("png", png_upload()),
            ("svg", svg_upload()),
            ("blank", None),
        )
        for index, (label, icon) in enumerate(cases):
            payload = {
                "slug": f"category-{index}",
                "title": f"دسته {index}",
                "_save": "Save",
            }
            if icon is not None:
                payload["icon"] = icon

            with self.subTest(format=label):
                response = self.client.post(
                    reverse("admin:catalog_category_add"),
                    payload,
                )
                self.assertEqual(response.status_code, 302)
                category = Category.objects.get(slug=f"category-{index}")
                self.assertEqual(bool(category.icon), icon is not None)

    def test_invalid_replacement_preserves_existing_icon(self):
        category = self.create_category(icon=png_upload("old.png"))
        old_name = category.icon.name
        old_path = category.icon.path

        response = self.client.post(
            reverse("admin:catalog_category_change", args=[category.id]),
            self.change_payload(
                category,
                icon=SimpleUploadedFile("unsafe.svg", b"<svg><script /></svg>"),
            ),
        )

        category.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(category.icon.name, old_name)
        self.assertTrue(os.path.exists(old_path))

    def test_update_without_file_preserves_existing_icon(self):
        category = self.create_category(icon=png_upload("old.png"))
        old_name = category.icon.name

        response = self.client.post(
            reverse("admin:catalog_category_change", args=[category.id]),
            self.change_payload(category, title="ابزار به‌روز"),
        )

        category.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(category.title, "ابزار به‌روز")
        self.assertEqual(category.icon.name, old_name)

    def test_replacing_icon_deletes_old_file_after_commit(self):
        category = self.create_category(icon=png_upload("old.png"))
        old_path = category.icon.path

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("admin:catalog_category_change", args=[category.id]),
                self.change_payload(category, icon=svg_upload(name="new.svg")),
            )

        category.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(category.icon.name.endswith(".svg"))
        self.assertTrue(os.path.exists(category.icon.path))
        self.assertFalse(os.path.exists(old_path))

    def test_clear_removes_database_reference_then_old_file(self):
        category = self.create_category(icon=png_upload("old.png"))
        old_path = category.icon.path

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("admin:catalog_category_change", args=[category.id]),
                self.change_payload(category, **{"icon-clear": "on"}),
            )

        category.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(category.icon)
        self.assertFalse(os.path.exists(old_path))

    def test_replacement_does_not_delete_a_shared_file(self):
        category = self.create_category(icon=png_upload("shared.png"))
        shared_path = category.icon.path
        Category.objects.create(
            slug="shared",
            title="دسته مشترک",
            icon=category.icon.name,
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("admin:catalog_category_change", args=[category.id]),
                self.change_payload(category, icon=svg_upload(name="new.svg")),
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(os.path.exists(shared_path))

    def test_storage_cleanup_failure_does_not_break_a_completed_replacement(self):
        category = self.create_category(icon=png_upload("old.png"))
        old_path = category.icon.path
        storage = category.icon.storage

        with patch.object(storage, "delete", side_effect=OSError("unavailable")):
            with self.assertLogs("django.test", level="ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.post(
                        reverse("admin:catalog_category_change", args=[category.id]),
                        self.change_payload(
                            category,
                            icon=svg_upload(name="new.svg"),
                        ),
                    )

        category.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(category.icon.name.endswith(".svg"))
        self.assertTrue(os.path.exists(category.icon.path))
        self.assertTrue(os.path.exists(old_path))

    def test_admin_delete_cleans_up_icon_after_commit(self):
        category = self.create_category(icon=png_upload("delete.png"))
        icon_path = category.icon.path

        with self.captureOnCommitCallbacks(execute=True):
            self.model_admin.delete_model(self.request, category)

        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
        self.assertFalse(os.path.exists(icon_path))

    def test_protected_delete_keeps_category_and_icon(self):
        category = self.create_category(icon=png_upload("protected.png"))
        icon_path = category.icon.path
        Product.objects.create(title="بیل", category=category, price=100_000)

        with self.assertRaises(ProtectedError):
            self.model_admin.delete_model(self.request, category)

        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
        self.assertTrue(os.path.exists(icon_path))
