from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import Order, OrderItem

from .models import Category, Product, ProductComment, ProductRating


PRODUCT_RESPONSE_KEYS = {
    "image",
    "images",
    "id",
    "title",
    "titleEn",
    "category",
    "categorySlug",
    "categories",
    "categorySlugs",
    "price",
    "oldPrice",
    "rating",
    "ratingCount",
    "badge",
    "colors",
    "features",
    "specs",
    "description",
    "warranty",
    "stock",
    "isActive",
}


class ProductApiContractTests(TestCase):
    def setUp(self):
        category = Category.objects.create(slug="tools", title="ابزار")
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000
        )
        self.related = Product.objects.create(
            title="شن‌کش", category=category, price=120_000
        )
        self.client = APIClient()

    def test_product_list_uses_current_product_contract(self):
        response = self.client.get("/api/products")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["ok"], True)
        self.assertEqual(len(response.data["data"]["items"]), 2)
        for product in response.data["data"]["items"]:
            self.assertEqual(set(product), PRODUCT_RESPONSE_KEYS)

    def test_product_detail_and_related_use_current_product_contract(self):
        response = self.client.get(f"/api/products/{self.product.id}")

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(set(data["product"]), PRODUCT_RESPONSE_KEYS)
        self.assertEqual(len(data["related"]), 1)
        self.assertEqual(set(data["related"][0]), PRODUCT_RESPONSE_KEYS)


class ProductFeedbackContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        self.other_user = get_user_model().objects.create_user(phone="09121111111")
        self.admin = get_user_model().objects.create_user(
            phone="09122222222", is_staff=True
        )
        category = Category.objects.create(slug="tools", title="ابزار")
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def purchase(self, user, status=Order.Status.PAID):
        order = Order.objects.create(
            code=f"ORDER-{user.id}-{Order.objects.count()}",
            status=status,
            user=user,
            full_name="کاربر آزمایشی",
            phone=user.phone,
            province="تهران",
            city="تهران",
            address="آدرس کامل خریدار",
            items_price=self.product.price,
            total_price=self.product.price,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            title=self.product.title,
            price=self.product.price,
            qty=1,
        )
        return order

    def create_comment(self, **payload):
        data = {"content": "این یک دیدگاه آزمایشی است", **payload}
        return self.client.post(
            f"/api/products/{self.product.id}/comments", data, format="json"
        )

    def test_purchaser_can_create_and_update_one_rating(self):
        self.purchase(self.user)

        created = self.client.put(
            f"/api/products/{self.product.id}/rating",
            {"rating": 5},
            format="json",
        )
        updated = self.client.put(
            f"/api/products/{self.product.id}/rating",
            {"rating": 3},
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(ProductRating.objects.count(), 1)
        self.assertEqual(ProductRating.objects.get().rating, 3)
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, 3)
        self.assertEqual(self.product.rating_count, 1)

    def test_non_purchaser_and_unpaid_customer_cannot_rate(self):
        unpaid = self.client.put(
            f"/api/products/{self.product.id}/rating",
            {"rating": 5},
            format="json",
        )
        self.purchase(self.user, status=Order.Status.PENDING)
        pending_order = self.client.put(
            f"/api/products/{self.product.id}/rating",
            {"rating": 5},
            format="json",
        )

        self.assertEqual(unpaid.status_code, 403)
        self.assertEqual(pending_order.status_code, 403)
        self.assertFalse(ProductRating.objects.exists())

    def test_rating_statistics_and_comments_are_independent(self):
        self.purchase(self.user)
        self.client.put(
            f"/api/products/{self.product.id}/rating",
            {"rating": 4},
            format="json",
        )
        comment = self.create_comment()

        stats = self.client.get(f"/api/products/{self.product.id}/rating")
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(ProductComment.objects.count(), 1)
        self.assertEqual(ProductRating.objects.count(), 1)
        self.assertEqual(stats.data["data"]["rating"]["average"], 4)
        self.assertEqual(stats.data["data"]["rating"]["count"], 1)

    def test_non_purchaser_can_submit_comment_and_question_as_pending(self):
        comment = self.create_comment()
        question = self.create_comment(
            content="آیا این محصول گارانتی دارد؟", type="question"
        )

        self.assertEqual(comment.status_code, 201)
        self.assertEqual(question.status_code, 201)
        self.assertEqual(
            list(ProductComment.objects.values_list("moderation_status", flat=True)),
            ["pending", "pending"],
        )
        self.assertEqual(
            set(ProductComment.objects.values_list("comment_type", flat=True)),
            {"comment", "question"},
        )

    def test_pending_and_rejected_customer_messages_are_not_public(self):
        pending_id = self.create_comment().data["data"]["comment"]["id"]
        ProductComment.objects.create(
            product=self.product,
            user=self.other_user,
            content="این پیام رد شده است",
            moderation_status=ProductComment.ModerationStatus.REJECTED,
        )

        public = APIClient().get(f"/api/products/{self.product.id}/comments")
        own = self.client.get(f"/api/products/{self.product.id}/comments")

        self.assertEqual(public.data["data"]["comments"], [])
        self.assertEqual(own.data["data"]["comments"][0]["id"], pending_id)
        self.assertEqual(own.data["data"]["comments"][0]["status"], "pending")

    def test_every_customer_reply_requires_independent_approval(self):
        parent = ProductComment.objects.create(
            product=self.product,
            user=self.other_user,
            content="پرسش تاییدشده",
            comment_type=ProductComment.Type.QUESTION,
            moderation_status=ProductComment.ModerationStatus.APPROVED,
        )
        reply = self.create_comment(
            content="پاسخ کاربر به گفتگو", parentId=parent.id
        )

        self.assertEqual(reply.status_code, 201)
        reply_obj = ProductComment.objects.get(pk=reply.data["data"]["comment"]["id"])
        self.assertEqual(reply_obj.parent, parent)
        self.assertEqual(reply_obj.comment_type, ProductComment.Type.QUESTION)
        self.assertEqual(reply_obj.moderation_status, "pending")
        public = APIClient().get(f"/api/products/{self.product.id}/comments")
        self.assertEqual(public.data["data"]["comments"][0]["replies"], [])

    def test_admin_can_moderate_and_official_response_is_immediately_visible(self):
        comment_id = self.create_comment().data["data"]["comment"]["id"]
        admin_client = APIClient()
        admin_client.force_authenticate(self.admin)

        approved = admin_client.patch(
            f"/api/admin/comments/{comment_id}",
            {"status": "approved"},
            format="json",
        )
        response = admin_client.post(
            f"/api/admin/comments/{comment_id}/responses",
            {"content": "پاسخ رسمی فروشگاه"},
            format="json",
        )

        self.assertEqual(approved.status_code, 200)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["data"]["comment"]["isAdminResponse"])
        self.assertEqual(response.data["data"]["comment"]["status"], "approved")
        public = APIClient().get(f"/api/products/{self.product.id}/comments")
        official = public.data["data"]["comments"][0]["replies"][0]
        self.assertTrue(official["isAdminResponse"])

    def test_customer_cannot_moderate_or_create_official_response(self):
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.other_user,
            content="پیام تاییدشده",
            moderation_status=ProductComment.ModerationStatus.APPROVED,
        )

        moderated = self.client.patch(
            f"/api/admin/comments/{comment.id}",
            {"status": "rejected"},
            format="json",
        )
        official = self.client.post(
            f"/api/admin/comments/{comment.id}/responses",
            {"content": "پاسخ جعلی"},
            format="json",
        )

        self.assertEqual(moderated.status_code, 403)
        self.assertEqual(official.status_code, 403)

    def test_admin_and_verified_purchase_flags_are_backend_derived(self):
        self.purchase(self.user)
        response = self.create_comment(
            isAdminResponse=True,
            isVerifiedPurchase=False,
        )
        comment = ProductComment.objects.get(pk=response.data["data"]["comment"]["id"])
        comment.moderation_status = ProductComment.ModerationStatus.APPROVED
        comment.save(update_fields=["moderation_status"])

        public = APIClient().get(f"/api/products/{self.product.id}/comments")
        data = public.data["data"]["comments"][0]
        self.assertFalse(data["isAdminResponse"])
        self.assertTrue(data["isVerifiedPurchase"])

    def test_non_purchaser_has_no_verified_purchase_indicator(self):
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.other_user,
            content="دیدگاه کاربر بدون خرید",
            moderation_status=ProductComment.ModerationStatus.APPROVED,
        )
        public = APIClient().get(f"/api/products/{self.product.id}/comments")
        self.assertEqual(public.data["data"]["comments"][0]["id"], comment.id)
        self.assertFalse(
            public.data["data"]["comments"][0]["isVerifiedPurchase"]
        )

    def test_my_comments_contract_and_owner_delete(self):
        comment = ProductComment.objects.create(
            product=self.product,
            user=self.user,
            content="دیدگاه شخصی کاربر",
        )
        listed = self.client.get("/api/auth/my-comments")
        row = listed.data["data"]["comments"][0]
        self.assertEqual(
            set(row),
            {
                "id",
                "content",
                "type",
                "status",
                "parentId",
                "createdAt",
                "productId",
                "productTitle",
                "isVerifiedPurchase",
            },
        )

        deleted = self.client.delete(
            "/api/auth/my-comments", {"commentId": comment.id}, format="json"
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(ProductComment.objects.filter(pk=comment.id).exists())
