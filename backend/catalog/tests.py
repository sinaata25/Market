from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Product, Review


class ReviewContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        category = Category.objects.create(
            slug="tools", title="ابزار", emoji="🌿"
        )
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000, emoji="🌿"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_user_can_submit_only_one_review_per_product(self):
        first = self.client.post(
            f"/api/products/{self.product.id}/reviews",
            {"rating": 5, "text": "محصول بسیار خوبی بود"},
            format="json",
        )
        second = self.client.post(
            f"/api/products/{self.product.id}/reviews",
            {"rating": 4, "text": "دیدگاه تکراری است"},
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(Review.objects.count(), 1)

    def test_deleting_own_review_recomputes_product_rating(self):
        review = Review.objects.create(
            product=self.product, user=self.user, rating=5, text="عالی بود"
        )
        self.product.rating = 5
        self.product.rating_count = 1
        self.product.save(update_fields=["rating", "rating_count"])

        response = self.client.delete(
            "/api/auth/my-reviews", {"reviewId": review.id}, format="json"
        )

        self.product.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.product.rating, 0)
        self.assertEqual(self.product.rating_count, 0)
