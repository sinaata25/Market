from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Category, Product, Review


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


class ReviewContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        category = Category.objects.create(slug="tools", title="ابزار")
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000
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

    def test_my_reviews_uses_current_product_reference_contract(self):
        Review.objects.create(
            product=self.product, user=self.user, rating=5, text="عالی بود"
        )

        response = self.client.get("/api/auth/my-reviews")

        self.assertEqual(response.status_code, 200)
        review = response.data["data"]["reviews"][0]
        self.assertEqual(
            set(review),
            {
                "id",
                "rating",
                "text",
                "createdAt",
                "productId",
                "productTitle",
            },
        )
