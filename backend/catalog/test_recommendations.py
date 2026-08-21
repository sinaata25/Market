from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase
from rest_framework.test import APIClient

from carts.models import Cart, CartItem

from .models import Category, Product, ProductRecommendation
from .recommendations import replace_product_recommendations


class RecommendationTestMixin:
    def make_product(self, title: str, *, stock: int = 5, active: bool = True):
        return Product.objects.create(
            title=title,
            category=self.category,
            price=100_000,
            stock=stock,
            is_active=active,
        )


class AdminProductRecommendationTests(RecommendationTestMixin, TestCase):
    def setUp(self):
        self.category = Category.objects.create(slug="tools", title="ابزار")
        admin = get_user_model().objects.create_user(
            phone="09121234567", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(admin)
        self.source = self.make_product("پمپ")
        self.targets = [self.make_product(f"مکمل {index}") for index in range(1, 5)]

    def payload(self, recommendation_ids):
        return {
            "title": self.source.title,
            "categorySlugs": [self.category.slug],
            "price": self.source.price,
            "stock": self.source.stock,
            "recommendedProductIds": recommendation_ids,
        }

    def update(self, recommendation_ids):
        return self.client.patch(
            f"/api/admin/products/{self.source.id}",
            self.payload(recommendation_ids),
            format="json",
        )

    def test_admin_can_add_one_and_then_three_ordered_recommendations(self):
        one = self.update([self.targets[0].id])
        three = self.update([target.id for target in self.targets[:3]])

        self.assertEqual(one.status_code, 200)
        self.assertEqual(three.status_code, 200)
        self.assertEqual(
            [item["id"] for item in three.data["data"]["product"]["recommendedProducts"]],
            [target.id for target in self.targets[:3]],
        )

    def test_product_can_be_created_with_recommendations(self):
        response = self.client.post(
            "/api/admin/products",
            {
                "title": "پمپ جدید",
                "categorySlugs": [self.category.slug],
                "price": 200_000,
                "stock": 2,
                "recommendedProductIds": [
                    self.targets[0].id,
                    self.targets[1].id,
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            [
                item["id"]
                for item in response.data["data"]["product"]["recommendedProducts"]
            ],
            [self.targets[0].id, self.targets[1].id],
        )

    def test_fourth_recommendation_is_rejected(self):
        response = self.update([target.id for target in self.targets])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductRecommendation.objects.count(), 0)

    def test_self_recommendation_is_rejected_without_changing_product(self):
        response = self.update([self.source.id])

        self.assertEqual(response.status_code, 422)
        self.assertEqual(ProductRecommendation.objects.count(), 0)

    def test_duplicate_recommendation_is_rejected(self):
        response = self.update([self.targets[0].id, self.targets[0].id])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductRecommendation.objects.count(), 0)

    def test_admin_can_replace_and_remove_recommendations(self):
        self.update([self.targets[0].id, self.targets[1].id])
        replaced = self.update([self.targets[2].id])
        removed = self.update([])

        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(
            [
                item["id"]
                for item in replaced.data["data"]["product"]["recommendedProducts"]
            ],
            [self.targets[2].id],
        )
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(ProductRecommendation.objects.count(), 0)

    def test_recommendations_are_directional_and_independent(self):
        replace_product_recommendations(self.source, [self.targets[0].id])
        replace_product_recommendations(self.targets[0], [self.targets[1].id])

        self.assertTrue(
            ProductRecommendation.objects.filter(
                source_product=self.source,
                recommended_product=self.targets[0],
            ).exists()
        )
        self.assertFalse(
            ProductRecommendation.objects.filter(
                source_product=self.targets[0],
                recommended_product=self.source,
            ).exists()
        )


class CartRecommendationTests(RecommendationTestMixin, TestCase):
    def setUp(self):
        self.category = Category.objects.create(slug="tools", title="ابزار")
        self.client = APIClient()
        self.source = self.make_product("پمپ")

    def add_to_cart(self, product: Product):
        return self.client.post(
            "/api/cart/items", {"productId": product.id, "qty": 1}, format="json"
        )

    def test_cart_returns_recommendations_and_add_to_cart_refreshes_them(self):
        target = self.make_product("شلنگ")
        replace_product_recommendations(self.source, [target.id])
        first = self.add_to_cart(self.source)

        self.assertEqual(
            first.data["data"]["cart"]["recommendations"][0]["product"]["id"],
            target.id,
        )
        added = self.add_to_cart(target)
        cart = added.data["data"]["cart"]
        self.assertEqual(cart["recommendations"], [])
        self.assertEqual(
            {item["product"]["id"] for item in cart["items"]},
            {self.source.id, target.id},
        )

    def test_cart_excludes_inactive_out_of_stock_and_already_added_products(self):
        inactive = self.make_product("غیرفعال", active=False)
        unavailable = self.make_product("ناموجود", stock=0)
        already_added = self.make_product("داخل سبد")
        replace_product_recommendations(
            self.source, [inactive.id, unavailable.id, already_added.id]
        )
        self.add_to_cart(self.source)
        response = self.add_to_cart(already_added)

        self.assertEqual(response.data["data"]["cart"]["recommendations"], [])

    def test_multiple_sources_deduplicate_target_and_include_context(self):
        second_source = self.make_product("ابزار")
        target = self.make_product("اتصال")
        replace_product_recommendations(self.source, [target.id])
        replace_product_recommendations(second_source, [target.id])
        self.add_to_cart(self.source)
        response = self.add_to_cart(second_source)

        recommendations = response.data["data"]["cart"]["recommendations"]
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(
            {item["id"] for item in recommendations[0]["recommendedFor"]},
            {self.source.id, second_source.id},
        )

    def test_cart_caps_the_offer_section_at_six_products(self):
        sources = [
            self.source,
            self.make_product("منبع دوم"),
            self.make_product("منبع سوم"),
        ]
        targets = [self.make_product(f"پیشنهاد {index}") for index in range(7)]
        replace_product_recommendations(sources[0], [item.id for item in targets[:3]])
        replace_product_recommendations(sources[1], [item.id for item in targets[3:6]])
        replace_product_recommendations(sources[2], [targets[6].id])
        self.add_to_cart(sources[0])
        self.add_to_cart(sources[1])
        response = self.add_to_cart(sources[2])

        self.assertEqual(
            len(response.data["data"]["cart"]["recommendations"]), 6
        )

    def test_cart_with_no_recommendations_remains_normal(self):
        response = self.add_to_cart(self.source)

        cart = response.data["data"]["cart"]
        self.assertEqual(cart["recommendations"], [])
        self.assertEqual(cart["itemsCount"], 1)

    @patch(
        "carts.services.cart_recommendation_dtos",
        side_effect=DatabaseError("recommendations unavailable"),
    )
    def test_recommendation_database_failure_does_not_break_cart(self, _selector):
        response = self.add_to_cart(self.source)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["cart"]["recommendations"], [])
        self.assertEqual(response.data["data"]["cart"]["itemsCount"], 1)

    def test_checkout_succeeds_without_recommendations(self):
        user = get_user_model().objects.create_user(phone="09120000000")
        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=self.source, qty=1)
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/orders",
            {
                "fullName": "کاربر آزمایشی",
                "province": "تهران",
                "city": "تهران",
                "address": "خیابان آزمایشی شماره ده",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
