from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import BlogCategory, BlogPost, BlogTag


class BlogModelTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(phone="09120000001")

    def make_post(self, **overrides):
        data = {
            "title": "راهنمای انتخاب ابزار باغبانی",
            "excerpt": "خلاصه کاربردی برای انتخاب ابزار مناسب",
            "content": "متن کامل و امن نوشته",
            "author": self.author,
        }
        data.update(overrides)
        return BlogPost.objects.create(**data)

    def test_published_post_requires_publication_date(self):
        with self.assertRaises(ValidationError):
            self.make_post(status=BlogPost.Status.PUBLISHED)

    def test_draft_rejects_publication_date(self):
        with self.assertRaises(ValidationError):
            self.make_post(published_at=timezone.now())

    def test_slug_is_generated_and_duplicate_titles_receive_unique_slugs(self):
        first = self.make_post()
        second = self.make_post()

        self.assertEqual(first.slug, "راهنمای-انتخاب-ابزار-باغبانی")
        self.assertEqual(second.slug, "راهنمای-انتخاب-ابزار-باغبانی-2")

    def test_published_queryset_excludes_drafts_and_future_posts(self):
        visible = self.make_post(
            title="منتشرشده",
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=1),
        )
        self.make_post(title="پیش‌نویس")
        self.make_post(
            title="زمان‌بندی‌شده",
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() + timedelta(days=1),
        )

        self.assertEqual(list(BlogPost.objects.published()), [visible])


class BlogApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(phone="09120000002", is_staff=True)
        self.normal_user = User.objects.create_user(phone="09120000003")
        self.category = BlogCategory.objects.create(name="آموزش", slug="education")
        self.other_category = BlogCategory.objects.create(name="اخبار", slug="news")
        self.tag = BlogTag.objects.create(name="باغبانی", slug="gardening")
        self.other_tag = BlogTag.objects.create(name="ابزار", slug="tools")
        self.published = BlogPost.objects.create(
            title="راهنمای باغبانی",
            excerpt="انتخاب ابزار مناسب باغبانی",
            content="این متن درباره نگهداری و انتخاب ابزار باغبانی است.",
            author=self.admin,
            category=self.category,
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(hours=1),
            seo_title="راهنمای کامل باغبانی",
        )
        self.published.tags.add(self.tag)
        self.draft = BlogPost.objects.create(
            title="پیش‌نویس محرمانه",
            excerpt="نباید نمایش داده شود",
            content="محتوای پیش‌نویس",
            author=self.admin,
        )

    def admin_client(self):
        client = APIClient()
        client.force_authenticate(self.admin)
        return client

    def payload(self, **overrides):
        payload = {
            "title": "نوشته تازه",
            "slug": "",
            "excerpt": "خلاصه نوشته تازه",
            "content": "محتوای کامل نوشته تازه",
            "categorySlug": self.category.slug,
            "tagSlugs": [self.tag.slug],
            "status": BlogPost.Status.DRAFT,
            "publishedAt": None,
            "seoTitle": "",
            "seoDescription": "",
        }
        payload.update(overrides)
        return payload

    def test_public_list_and_detail_only_return_published_posts(self):
        listed = self.client.get("/api/blog/posts")
        detail = self.client.get(f"/api/blog/posts/{self.published.slug}")
        draft_detail = self.client.get(f"/api/blog/posts/{self.draft.slug}")

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["data"]["total"], 1)
        self.assertEqual(listed.data["data"]["items"][0]["id"], self.published.id)
        self.assertNotIn("content", listed.data["data"]["items"][0])
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["post"]["content"], self.published.content)
        self.assertEqual(draft_detail.status_code, 404)

    def test_public_filters_search_and_pagination(self):
        second = BlogPost.objects.create(
            title="اخبار بازار ابزار",
            excerpt="گزارش بازار",
            content="تحلیل قیمت ابزار",
            author=self.admin,
            category=self.other_category,
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now() - timedelta(minutes=10),
        )
        second.tags.add(self.other_tag)

        by_category = self.client.get("/api/blog/posts?category=education")
        by_tag = self.client.get("/api/blog/posts?tag=tools")
        by_search = self.client.get("/api/blog/posts?search=نگهداری")
        paged = self.client.get("/api/blog/posts?perPage=1&page=2")

        self.assertEqual(by_category.data["data"]["total"], 1)
        self.assertEqual(by_tag.data["data"]["items"][0]["id"], second.id)
        self.assertEqual(by_search.data["data"]["items"][0]["id"], self.published.id)
        self.assertEqual(paged.data["data"]["pages"], 2)
        self.assertEqual(len(paged.data["data"]["items"]), 1)

    def test_invalid_pagination_returns_validation_error(self):
        response = self.client.get("/api/blog/posts?page=bad")

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.data["ok"])

    def test_public_taxonomies_only_include_values_used_by_visible_posts(self):
        categories = self.client.get("/api/blog/categories")
        tags = self.client.get("/api/blog/tags")

        self.assertEqual(
            [item["slug"] for item in categories.data["data"]["categories"]],
            [self.category.slug],
        )
        self.assertEqual(
            [item["slug"] for item in tags.data["data"]["tags"]],
            [self.tag.slug],
        )

    def test_staff_can_create_update_and_delete_post(self):
        client = self.admin_client()
        created = client.post("/api/admin/blog/posts", self.payload(), format="json")
        post_id = created.data["data"]["post"]["id"]
        updated = client.patch(
            f"/api/admin/blog/posts/{post_id}",
            {"title": "عنوان ویرایش‌شده"},
            format="json",
        )
        deleted = client.delete(f"/api/admin/blog/posts/{post_id}")

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["data"]["post"]["title"], "عنوان ویرایش‌شده")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(BlogPost.objects.filter(pk=post_id).exists())

    def test_staff_can_publish_and_unpublish(self):
        client = self.admin_client()
        published = client.post(f"/api/admin/blog/posts/{self.draft.id}/publish", {}, format="json")
        public_detail = self.client.get(f"/api/blog/posts/{self.draft.slug}")
        unpublished = client.post(
            f"/api/admin/blog/posts/{self.draft.id}/unpublish", {}, format="json"
        )
        hidden_again = self.client.get(f"/api/blog/posts/{self.draft.slug}")

        self.assertEqual(published.status_code, 200)
        self.assertEqual(public_detail.status_code, 200)
        self.assertEqual(unpublished.status_code, 200)
        self.assertEqual(hidden_again.status_code, 404)

    def test_published_create_without_date_returns_validation_error(self):
        response = self.admin_client().post(
            "/api/admin/blog/posts",
            self.payload(status=BlogPost.Status.PUBLISHED, publishedAt=None),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["ok"])

    def test_normal_and_anonymous_users_cannot_modify_posts(self):
        normal_client = APIClient()
        normal_client.force_authenticate(self.normal_user)

        normal = normal_client.post("/api/admin/blog/posts", self.payload(), format="json")
        anonymous = self.client.delete(f"/api/admin/blog/posts/{self.published.id}")

        self.assertEqual(normal.status_code, 403)
        self.assertEqual(anonymous.status_code, 403)
        self.assertTrue(BlogPost.objects.filter(pk=self.published.id).exists())

    def test_staff_can_manage_categories_and_tags(self):
        client = self.admin_client()
        category = client.post(
            "/api/admin/blog/categories",
            {"name": "راهنما", "slug": "guides", "description": ""},
            format="json",
        )
        tag = client.post(
            "/api/admin/blog/tags",
            {"name": "ایمنی", "slug": "safety"},
            format="json",
        )

        self.assertEqual(category.status_code, 201)
        self.assertEqual(tag.status_code, 201)
        self.assertTrue(BlogCategory.objects.filter(slug="guides").exists())
        self.assertTrue(BlogTag.objects.filter(slug="safety").exists())

    def test_invalid_featured_image_is_rejected(self):
        client = self.admin_client()
        response = client.post(
            f"/api/admin/blog/posts/{self.draft.id}/featured-image",
            {"file": self._invalid_upload()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 422)
        self.assertFalse(response.data["ok"])

    @staticmethod
    def _invalid_upload():
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile("fake.jpg", b"not-an-image", content_type="image/jpeg")
