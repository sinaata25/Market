from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class AdminValidationTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(
            phone="09121234567", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(admin)

    def test_invalid_page_returns_validation_error(self):
        response = self.client.get("/api/admin/products?page=not-a-number")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["ok"], False)
