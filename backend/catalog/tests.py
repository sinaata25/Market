from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import Order, OrderItem

from .models import (
    Category,
    Product,
    ProductComment,
    ProductRating,
    ProductSpecification,
    SpecificationKey,
)


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
    "brand",
    "price",
    "oldPrice",
    "rating",
    "ratingCount",
    "badge",
    "colors",
    "features",
    "description",
    "warranty",
    "stock",
    "isActive",
    "isBestSeller",
    "bestSellerPosition",
    "isIncredible",
    "incrediblePosition",
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
        self.assertEqual(
            set(data["product"]), PRODUCT_RESPONSE_KEYS | {"specifications"}
        )
        self.assertEqual(data["product"]["specifications"], [])
        self.assertEqual(len(data["related"]), 1)
        self.assertEqual(set(data["related"][0]), PRODUCT_RESPONSE_KEYS)

    def test_product_without_warranty_returns_null_not_a_default_value(self):
        self.assertEqual(self.product.warranty, "")

        list_response = self.client.get("/api/products")
        detail_response = self.client.get(f"/api/products/{self.product.id}")

        listed = next(
            item
            for item in list_response.data["data"]["items"]
            if item["id"] == self.product.id
        )
        self.assertIsNone(listed["warranty"])
        self.assertIsNone(detail_response.data["data"]["product"]["warranty"])

    def test_product_with_warranty_returns_its_actual_value(self):
        self.product.warranty = "۱۸ ماه گارانتی شرکتی"
        self.product.save(update_fields=["warranty"])

        response = self.client.get(f"/api/products/{self.product.id}")

        self.assertEqual(
            response.data["data"]["product"]["warranty"], "۱۸ ماه گارانتی شرکتی"
        )


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


class ProductCompareApiTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.other_category = Category.objects.create(
            slug="seeds", title="بذر و نهال"
        )
        self.weight_key = SpecificationKey.objects.create(name="وزن")
        self.power_key = SpecificationKey.objects.create(name="توان")
        self.material_key = SpecificationKey.objects.create(name="جنس")
        self.client = APIClient()

    def make_product(self, title, *, category=None, price=100_000, is_active=True):
        return Product.objects.create(
            title=title,
            category=category or self.category,
            price=price,
            is_active=is_active,
        )

    def add_spec(self, product, key, value, position=0):
        ProductSpecification.objects.create(
            product=product, key=key, value=value, position=position
        )

    def compare(self, product_ids):
        return self.client.post(
            "/api/products/compare", {"productIds": product_ids}, format="json"
        )

    def test_compares_two_products_from_same_category(self):
        a = self.make_product("محصول الف")
        b = self.make_product("محصول ب")

        response = self.compare([a.id, b.id])

        self.assertEqual(response.status_code, 200)
        items = response.data["data"]["items"]
        self.assertEqual([item["id"] for item in items], [a.id, b.id])

    def test_compares_three_four_and_five_products(self):
        products = [self.make_product(f"محصول {i}") for i in range(5)]

        for count in (3, 4, 5):
            ids = [p.id for p in products[:count]]
            response = self.compare(ids)
            self.assertEqual(response.status_code, 200, count)
            self.assertEqual(len(response.data["data"]["items"]), count)

    def test_rejects_a_sixth_product(self):
        products = [self.make_product(f"محصول {i}") for i in range(6)]

        response = self.compare([p.id for p in products])

        self.assertEqual(response.status_code, 400)

    def test_rejects_single_product(self):
        a = self.make_product("محصول تنها")

        response = self.compare([a.id])

        self.assertEqual(response.status_code, 400)

    def test_rejects_products_from_incompatible_categories(self):
        a = self.make_product("محصول ابزار", category=self.category)
        b = self.make_product("محصول بذر", category=self.other_category)

        response = self.compare([a.id, b.id])

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.data["ok"])

    def test_products_sharing_a_secondary_category_are_compatible(self):
        a = self.make_product("محصول اول", category=self.category)
        b = self.make_product("محصول دوم", category=self.other_category)
        b.categories.add(self.category)

        response = self.compare([a.id, b.id])

        self.assertEqual(response.status_code, 200)

    def test_rejects_duplicate_product_ids(self):
        a = self.make_product("محصول تکراری")

        response = self.compare([a.id, a.id])

        self.assertEqual(response.status_code, 409)

    def test_rejects_nonexistent_product_id(self):
        a = self.make_product("محصول موجود")

        response = self.compare([a.id, 999999])

        self.assertEqual(response.status_code, 409)

    def test_rejects_inactive_product(self):
        a = self.make_product("محصول فعال")
        b = self.make_product("محصول غیرفعال", is_active=False)

        response = self.compare([a.id, b.id])

        self.assertEqual(response.status_code, 409)

    def test_specification_union_and_missing_values(self):
        a = self.make_product("محصول اول")
        b = self.make_product("محصول دوم")
        c = self.make_product("محصول سوم")
        self.add_spec(a, self.weight_key, "۱ کیلوگرم", position=0)
        self.add_spec(a, self.power_key, "۵۰۰ وات", position=1)
        self.add_spec(b, self.weight_key, "۲ کیلوگرم", position=0)
        self.add_spec(c, self.power_key, "۷۰۰ وات", position=0)
        self.add_spec(c, self.material_key, "استیل", position=1)

        response = self.compare([a.id, b.id, c.id])

        items = response.data["data"]["items"]
        specs_by_id = {
            item["id"]: {spec["slug"]: spec["value"] for spec in item["specifications"]}
            for item in items
        }
        union_keys = {
            spec["slug"]
            for item in items
            for spec in item["specifications"]
        }
        self.assertEqual(
            union_keys,
            {self.weight_key.slug, self.power_key.slug, self.material_key.slug},
        )
        # محصول ب مقدار «توان» و «جنس» ندارد — باید غایب باشد نه خالی
        self.assertNotIn(self.power_key.slug, specs_by_id[b.id])
        self.assertNotIn(self.material_key.slug, specs_by_id[b.id])
        self.assertEqual(specs_by_id[a.id][self.weight_key.slug], "۱ کیلوگرم")

    def test_response_is_efficient(self):
        products = [self.make_product(f"محصول {i}") for i in range(5)]
        for product in products:
            self.add_spec(product, self.weight_key, "۱ کیلوگرم")

        # ثابت (مستقل از تعداد محصولات): محصول+دسته+برند، دسته‌های اضافه، تصاویر، مشخصات
        with self.assertNumQueries(4):
            response = self.compare([p.id for p in products])

        self.assertEqual(response.status_code, 200)


class BestSellerApiTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.client = APIClient()

    def make_product(self, title, *, is_best_seller=False, position=0, is_active=True):
        return Product.objects.create(
            title=title,
            category=self.category,
            price=100_000,
            is_active=is_active,
            is_best_seller=is_best_seller,
            best_seller_position=position,
        )

    def test_only_admin_selected_products_are_returned(self):
        featured = self.make_product("محصول ویژه", is_best_seller=True)
        self.make_product("محصول عادی")

        response = self.client.get("/api/products?bestSeller=true")

        self.assertEqual(response.status_code, 200)
        items = response.data["data"]["items"]
        self.assertEqual([item["id"] for item in items], [featured.id])

    def test_inactive_best_seller_is_not_publicly_visible(self):
        self.make_product("محصول غیرفعال", is_best_seller=True, is_active=False)

        response = self.client.get("/api/products?bestSeller=true")

        self.assertEqual(response.data["data"]["total"], 0)

    def test_featured_sort_respects_admin_position(self):
        third = self.make_product("سوم", is_best_seller=True, position=3)
        first = self.make_product("اول", is_best_seller=True, position=1)
        second = self.make_product("دوم", is_best_seller=True, position=2)

        response = self.client.get(
            "/api/products?bestSeller=true&sort=featured"
        )

        items = response.data["data"]["items"]
        self.assertEqual(
            [item["id"] for item in items], [first.id, second.id, third.id]
        )

    def test_best_seller_flag_does_not_affect_real_rating_data(self):
        product = self.make_product("محصول با امتیاز")
        product.rating = 4.5
        product.rating_count = 20
        product.save(update_fields=["rating", "rating_count"])

        response = self.client.get(f"/api/products/{product.id}")
        data = response.data["data"]["product"]

        self.assertEqual(data["isBestSeller"], False)
        self.assertEqual(data["rating"], 4.5)
        self.assertEqual(data["ratingCount"], 20)
