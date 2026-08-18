from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .definitions import (
    PAGE_DEFINITIONS,
    SUPPORTED_PAGE_KEYS,
    default_content,
    fields_for_page,
)
from .models import StaticPage


def response_page(response):
    return response.data["data"]["page"]


class StaticPageDefaultsTests(TestCase):
    def test_data_migration_seeds_every_supported_page_with_current_defaults(self):
        pages = {page.key: page for page in StaticPage.objects.all()}

        self.assertEqual(tuple(PAGE_DEFINITIONS), SUPPORTED_PAGE_KEYS)
        self.assertEqual(set(pages), set(SUPPORTED_PAGE_KEYS))
        for key in SUPPORTED_PAGE_KEYS:
            with self.subTest(key=key):
                self.assertEqual(pages[key].content, default_content(key))
                self.assertIsNone(pages[key].updated_by)

    def test_model_rejects_an_arbitrary_page_key(self):
        page = StaticPage(key="arbitrary", content={})

        with self.assertRaises(ValidationError):
            page.save()


class PublicStaticPageApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_detail_returns_seeded_content(self):
        response = self.client.get("/api/content/pages/about")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ok"])
        self.assertEqual(
            response.data["data"]["page"],
            {"key": "about", "content": default_content("about")},
        )

    def test_public_list_without_filter_returns_all_pages_in_canonical_order(self):
        response = self.client.get("/api/content/pages")

        self.assertEqual(response.status_code, 200)
        pages = response.data["data"]["pages"]
        self.assertEqual([page["key"] for page in pages], list(SUPPORTED_PAGE_KEYS))
        self.assertEqual(pages[0]["content"], default_content(SUPPORTED_PAGE_KEYS[0]))

    def test_public_batch_filters_deduplicates_and_preserves_requested_order(self):
        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/content/pages", {"keys": "support,contact,support"}
            )

        self.assertEqual(response.status_code, 200)
        pages = response.data["data"]["pages"]
        self.assertEqual([page["key"] for page in pages], ["support", "contact"])
        self.assertEqual(pages[0]["content"], default_content("support"))

    def test_missing_database_row_uses_the_controlled_default(self):
        StaticPage.objects.filter(key="shipping").delete()

        detail = self.client.get("/api/content/pages/shipping")
        batch = self.client.get("/api/content/pages", {"keys": "shipping"})

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            response_page(detail)["content"], default_content("shipping")
        )
        self.assertEqual(
            batch.data["data"]["pages"][0]["content"],
            default_content("shipping"),
        )

    def test_invalid_stored_structure_also_falls_back_safely(self):
        StaticPage.objects.filter(key="returns").update(
            content={"unexpected": "value"}
        )

        response = self.client.get("/api/content/pages/returns")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_page(response)["content"], default_content("returns"))

    def test_invalid_public_keys_are_controlled(self):
        detail = self.client.get("/api/content/pages/not-supported")
        unknown_batch = self.client.get(
            "/api/content/pages", {"keys": "about,not-supported"}
        )
        blank_batch = self.client.get("/api/content/pages?keys=")
        malformed_batch = self.client.get("/api/content/pages?keys=about,,contact")

        self.assertEqual(detail.status_code, 404)
        self.assertFalse(detail.data["ok"])
        for response in (unknown_batch, blank_batch, malformed_batch):
            self.assertEqual(response.status_code, 422)
            self.assertFalse(response.data["ok"])


class AdminStaticPageApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            phone="09120000041", name="مدیر محتوا", is_staff=True
        )
        self.normal_user = User.objects.create_user(phone="09120000042")
        self.seo_manager = User.objects.create_user(
            phone="09120000043", is_seo_manager=True
        )
        self.staff_client = APIClient()
        self.staff_client.force_authenticate(self.staff)

    def authenticated_client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def patch(self, key: str, fields, **extra):
        payload = {"fields": fields, **extra}
        return self.staff_client.patch(
            f"/api/admin/content/pages/{key}", payload, format="json"
        )

    def assert_field_error(self, response, field_id: str):
        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.data["ok"])
        self.assertIn(field_id, response.data["data"]["fieldErrors"])

    def test_anonymous_customer_and_seo_manager_cannot_access_content_admin(self):
        clients = {
            "anonymous": APIClient(),
            "customer": self.authenticated_client(self.normal_user),
            "seo-manager": self.authenticated_client(self.seo_manager),
        }
        original = StaticPage.objects.get(key="about").content["hero"]["title"]

        for role, client in clients.items():
            with self.subTest(role=role, method="list"):
                self.assertEqual(
                    client.get("/api/admin/content/pages").status_code, 403
                )
            with self.subTest(role=role, method="detail"):
                self.assertEqual(
                    client.get("/api/admin/content/pages/about").status_code,
                    403,
                )
            with self.subTest(role=role, method="patch"):
                response = client.patch(
                    "/api/admin/content/pages/about",
                    {"fields": {"hero.title": "تغییر غیرمجاز"}},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)

        self.assertEqual(
            StaticPage.objects.get(key="about").content["hero"]["title"],
            original,
        )

    def test_staff_list_uses_fixed_page_inventory_and_metadata_contract(self):
        response = self.staff_client.get("/api/admin/content/pages")

        self.assertEqual(response.status_code, 200)
        pages = response.data["data"]["pages"]
        self.assertEqual([page["key"] for page in pages], list(SUPPORTED_PAGE_KEYS))
        self.assertEqual(
            set(pages[0]),
            {"key", "label", "path", "updatedAt", "updatedBy"},
        )
        self.assertIsNotNone(pages[0]["updatedAt"])
        self.assertIsNone(pages[0]["updatedBy"])

    def test_staff_detail_returns_grouped_descriptors_without_raw_json(self):
        response = self.staff_client.get("/api/admin/content/pages/contact")

        self.assertEqual(response.status_code, 200)
        page = response_page(response)
        self.assertNotIn("content", page)
        self.assertEqual(
            set(page),
            {"key", "label", "path", "updatedAt", "updatedBy", "fields"},
        )
        self.assertEqual(
            [field["id"] for field in page["fields"]],
            [field.id for field in fields_for_page("contact")],
        )
        by_id = {field["id"]: field for field in page["fields"]}
        phone = by_id["ways.0.phoneNumber"]
        self.assertEqual(phone["control"], "tel")
        self.assertEqual(phone["dir"], "ltr")
        self.assertEqual(phone["maxLength"], 25)
        self.assertIn("help", phone)
        self.assertTrue(phone["required"])
        self.assertTrue(phone["group"])

    def test_missing_admin_row_exposes_default_fields_and_null_metadata(self):
        StaticPage.objects.filter(key="warranty").delete()

        response = self.staff_client.get("/api/admin/content/pages/warranty")

        self.assertEqual(response.status_code, 200)
        page = response_page(response)
        self.assertIsNone(page["updatedAt"])
        self.assertIsNone(page["updatedBy"])
        fields = {field["id"]: field["value"] for field in page["fields"]}
        self.assertEqual(fields["title"], default_content("warranty")["title"])

    def test_staff_update_persists_editor_and_is_immediately_public(self):
        response = self.patch(
            "about",
            {
                "hero.title": "  عنوان تازه درباره ما  ",
                "story.paragraphs.0": "روایت تازه مجموعه توانا",
            },
        )

        self.assertEqual(response.status_code, 200)
        page = response_page(response)
        values = {field["id"]: field["value"] for field in page["fields"]}
        self.assertEqual(values["hero.title"], "عنوان تازه درباره ما")
        self.assertEqual(page["updatedBy"], self.staff.name)
        self.assertIsNotNone(page["updatedAt"])

        stored = StaticPage.objects.get(key="about")
        self.assertEqual(stored.content["hero"]["title"], "عنوان تازه درباره ما")
        self.assertEqual(stored.updated_by, self.staff)

        public = APIClient().get("/api/content/pages/about")
        self.assertEqual(
            response_page(public)["content"]["hero"]["title"],
            "عنوان تازه درباره ما",
        )

        listed = self.staff_client.get("/api/admin/content/pages")
        summary = next(
            item for item in listed.data["data"]["pages"] if item["key"] == "about"
        )
        self.assertEqual(summary["updatedBy"], self.staff.name)
        self.assertEqual(summary["updatedAt"], stored.updated_at.isoformat())

    def test_staff_can_edit_each_supported_page_without_changing_its_shape(self):
        for key in SUPPORTED_PAGE_KEYS:
            with self.subTest(key=key):
                definitions = fields_for_page(key)
                changed_field = definitions[0]
                untouched_field = definitions[1]
                untouched_value = next(
                    field["value"]
                    for field in response_page(
                        self.staff_client.get(
                            f"/api/admin/content/pages/{key}"
                        )
                    )["fields"]
                    if field["id"] == untouched_field.id
                )
                new_value = f"ویرایش آزمایشی {key}"

                response = self.patch(key, {changed_field.id: new_value})

                self.assertEqual(response.status_code, 200)
                values = {
                    field["id"]: field["value"]
                    for field in response_page(response)["fields"]
                }
                self.assertEqual(values[changed_field.id], new_value)
                self.assertEqual(values[untouched_field.id], untouched_value)
                self.assertEqual(
                    len(values), len(definitions)
                )

    def test_update_recreates_a_missing_supported_row(self):
        StaticPage.objects.filter(key="track-order").delete()

        response = self.patch("track-order", {"title": "پیگیری خرید"})

        self.assertEqual(response.status_code, 200)
        page = StaticPage.objects.get(key="track-order")
        self.assertEqual(page.content["title"], "پیگیری خرید")
        self.assertEqual(page.updated_by, self.staff)

    def test_patch_requires_only_a_nonempty_fields_object(self):
        missing = self.staff_client.patch(
            "/api/admin/content/pages/about", {}, format="json"
        )
        empty = self.patch("about", {})
        not_object = self.staff_client.patch(
            "/api/admin/content/pages/about", {"fields": []}, format="json"
        )
        extra = self.patch(
            "about", {"hero.title": "عنوان"}, content={"hero": {}}
        )

        self.assert_field_error(missing, "fields")
        self.assert_field_error(empty, "fields")
        self.assert_field_error(not_object, "fields")
        self.assert_field_error(extra, "content")

    def test_unknown_and_prototype_like_field_ids_are_rejected(self):
        for field_id in ("hero.unknown", "__proto__", "constructor.prototype"):
            with self.subTest(field_id=field_id):
                response = self.patch("about", {field_id: "مقدار"})
                self.assert_field_error(response, field_id)

    def test_blank_and_too_long_fields_are_rejected(self):
        blank = self.patch("about", {"hero.title": "   "})
        title_definition = next(
            field for field in fields_for_page("about") if field.id == "hero.title"
        )
        too_long = self.patch(
            "about", {"hero.title": "x" * (title_definition.max_length + 1)}
        )

        self.assert_field_error(blank, "hero.title")
        self.assert_field_error(too_long, "hero.title")

    def test_nonstring_values_are_rejected_without_coercion(self):
        for value in (123, True, {"nested": "value"}, ["value"]):
            with self.subTest(value=value):
                response = self.patch("about", {"hero.title": value})
                self.assert_field_error(response, "hero.title")

    def test_phone_unsafe_link_and_control_characters_are_rejected(self):
        invalid_phones = [
            self.patch("contact", {"ways.0.phoneNumber": value})
            for value in ("شماره نامعتبر", "1-----")
        ]
        unsafe_link = self.patch(
            "support", {"contact.onlineUrl": "javascript:alert(1)"}
        )
        control_character = self.patch(
            "about", {"hero.title": "عنوان\u0000مخرب"}
        )

        for response in invalid_phones:
            self.assert_field_error(response, "ways.0.phoneNumber")
        self.assert_field_error(unsafe_link, "contact.onlineUrl")
        self.assert_field_error(control_character, "hero.title")

    def test_malformed_online_urls_return_validation_errors_instead_of_500(self):
        for url in ("https://[", "https://[::1", "https://／example.com"):
            with self.subTest(url=url):
                response = self.patch("support", {"contact.onlineUrl": url})
                self.assert_field_error(response, "contact.onlineUrl")

    def test_html_markup_and_mismatched_phone_display_are_rejected(self):
        html = self.patch(
            "about", {"hero.title": "<script>alert('xss')</script>"}
        )
        mismatch = self.patch(
            "contact", {"ways.0.phoneNumber": "02111111111"}
        )

        self.assert_field_error(html, "hero.title")
        self.assert_field_error(mismatch, "ways.0.label")

    def test_safe_external_and_anchor_links_are_accepted(self):
        for url in ("https://example.com/chat", "http://example.com/chat", "#"):
            with self.subTest(url=url):
                response = self.patch("support", {"contact.onlineUrl": url})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    StaticPage.objects.get(key="support").content["contact"][
                        "onlineUrl"
                    ],
                    url,
                )

    def test_internal_online_link_is_not_admin_editable(self):
        response = self.patch("support", {"contact.onlineUrl": "/contact"})

        self.assert_field_error(response, "contact.onlineUrl")

    def test_invalid_admin_page_key_is_controlled_and_cannot_be_created(self):
        detail = self.staff_client.get(
            "/api/admin/content/pages/arbitrary-page"
        )
        update = self.patch("arbitrary-page", {"title": "صفحه دلخواه"})

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(update.status_code, 404)
        self.assertFalse(StaticPage.objects.filter(key="arbitrary-page").exists())
