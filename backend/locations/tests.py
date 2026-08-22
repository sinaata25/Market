from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Address
from carts.models import Cart, CartItem
from catalog.models import Category, Product
from orders.models import Order

from .registry import (
    CityProvinceMismatch,
    get_registry,
    resolve_location_names,
)


def location_ids(province: str, city: str) -> tuple[str, str]:
    resolved = resolve_location_names(province, city)
    assert resolved.city_id is not None
    return resolved.province_id, resolved.city_id


class LocationDatasetTests(TestCase):
    def test_dataset_is_complete_and_official_codes_are_unique(self):
        registry = get_registry()

        self.assertEqual(registry.year, 1404)
        self.assertEqual(len(registry.provinces), 31)
        self.assertEqual(len(registry.provinces_by_id), 31)
        self.assertEqual(len(registry.cities_by_id), 1481)
        self.assertEqual(
            sum(len(province.cities) for province in registry.provinces),
            1481,
        )
        self.assertTrue(all(len(code) == 2 for code in registry.provinces_by_id))
        self.assertTrue(all(len(code) == 4 for code in registry.cities_by_id))

    def test_name_normalization_accepts_arabic_character_variants(self):
        resolved = resolve_location_names("فارس", "شيراز")

        self.assertEqual(resolved.city_name, "شیراز")
        self.assertIsNotNone(resolved.city_id)

    def test_wrong_province_city_pair_is_not_resolved(self):
        with self.assertRaises(CityProvinceMismatch):
            resolve_location_names("فارس", "تبریز")

    def test_same_name_cities_are_preserved_with_codes_and_counties(self):
        registry = get_registry()
        kerman = registry.provinces_by_name["کرمان"]
        aliabad = [city for city in kerman.cities if city.name == "علی آباد"]

        self.assertEqual(len(aliabad), 2)
        self.assertEqual(len({city.id for city in aliabad}), 2)
        self.assertEqual(
            {city.county_name for city in aliabad}, {"جیرفت", "ارزوییه"}
        )


class LocationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_province_list_is_public_complete_sorted_and_cacheable(self):
        response = self.client.get("/api/locations/provinces")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ok"])
        self.assertEqual(response.data["data"]["version"], "1404")
        provinces = response.data["data"]["provinces"]
        self.assertEqual(len(provinces), 31)
        self.assertEqual(
            [item["name"] for item in provinces],
            sorted(item["name"] for item in provinces),
        )
        self.assertEqual(
            next(item for item in provinces if item["name"] == "فارس")["id"],
            "07",
        )
        self.assertIn("public", response["Cache-Control"])
        self.assertIn("max-age=86400", response["Cache-Control"])

    def test_city_list_is_scoped_to_province_and_exposes_disambiguator(self):
        response = self.client.get("/api/locations/provinces/08/cities")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["province"]["name"], "کرمان")
        cities = response.data["data"]["cities"]
        self.assertEqual(
            [item["name"] for item in cities],
            sorted(item["name"] for item in cities),
        )
        aliabad = [item for item in cities if item["name"] == "علی آباد"]
        self.assertEqual(len(aliabad), 2)
        self.assertEqual(
            {item["countyName"] for item in aliabad}, {"جیرفت", "ارزوییه"}
        )
        self.assertTrue(all(set(item) == {"id", "name", "countyName"} for item in cities))

    def test_unknown_province_code_returns_standard_404(self):
        response = self.client.get("/api/locations/provinces/99/cities")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"ok": False, "error": "استان یافت نشد"})


class AddressLocationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        self.other_user = get_user_model().objects.create_user(phone="09120000000")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payload(self, **changes):
        payload = {
            "title": "خانه",
            "fullName": "کاربر آزمایشی",
            "phone": "09121234567",
            "province": "فارس",
            "city": "شیراز",
            "address": "خیابان آزمایشی شماره ده",
            "postalCode": "7188812345",
            "isDefault": False,
        }
        payload.update(changes)
        return payload

    def test_address_creation_with_official_ids_persists_canonical_snapshot(self):
        province_id, city_id = location_ids("فارس", "شیراز")
        response = self.client.post(
            "/api/auth/addresses",
            self.payload(provinceId=province_id, cityId=city_id),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        address = Address.objects.get(user=self.user)
        self.assertEqual(address.province, "فارس")
        self.assertEqual(address.city, "شیراز")
        self.assertEqual(address.province_code, province_id)
        self.assertEqual(address.city_code, city_id)
        self.assertEqual(response.data["data"]["address"]["provinceId"], province_id)
        self.assertEqual(response.data["data"]["address"]["cityId"], city_id)
        self.assertTrue(address.is_default)

    def test_address_creation_can_resolve_canonical_names_from_ids_only(self):
        province_id, city_id = location_ids("فارس", "شیراز")
        payload = self.payload(provinceId=province_id, cityId=city_id)
        payload.pop("province")
        payload.pop("city")

        response = self.client.post(
            "/api/auth/addresses", payload, format="json"
        )

        self.assertEqual(response.status_code, 201)
        address = Address.objects.get(user=self.user)
        self.assertEqual(
            (address.province, address.city, address.province_code, address.city_code),
            ("فارس", "شیراز", province_id, city_id),
        )

    def test_backward_compatible_name_only_creation_is_validated_and_coded(self):
        response = self.client.post(
            "/api/auth/addresses", self.payload(city="شيراز"), format="json"
        )

        self.assertEqual(response.status_code, 201)
        address = Address.objects.get(user=self.user)
        self.assertEqual((address.province, address.city), ("فارس", "شیراز"))
        self.assertIsNotNone(address.province_code)
        self.assertIsNotNone(address.city_code)

    def test_duplicate_name_selection_persists_the_selected_official_city_id(self):
        registry = get_registry()
        kerman = registry.provinces_by_name["کرمان"]
        selected = next(
            city
            for city in kerman.cities
            if city.name == "علی آباد" and city.county_name == "ارزوییه"
        )

        response = self.client.post(
            "/api/auth/addresses",
            self.payload(
                province="کرمان",
                city="علی آباد",
                provinceId=kerman.id,
                cityId=selected.id,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Address.objects.get().city_code, selected.id)

    def test_name_only_duplicate_pair_is_valid_without_guessing_a_city_code(self):
        response = self.client.post(
            "/api/auth/addresses",
            self.payload(province="کرمان", city="علی آباد"),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        address = Address.objects.get()
        self.assertEqual(address.province_code, "08")
        self.assertIsNone(address.city_code)

    def test_wrong_province_city_name_combination_is_rejected(self):
        response = self.client.post(
            "/api/auth/addresses",
            self.payload(province="فارس", city="تبریز"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("متعلق به استان", response.data["error"])
        self.assertFalse(Address.objects.exists())

    def test_wrong_province_city_id_combination_is_rejected(self):
        fars_id, _ = location_ids("فارس", "شیراز")
        _, tabriz_id = location_ids("آذربایجان شرقی", "تبریز")
        response = self.client.post(
            "/api/auth/addresses",
            self.payload(provinceId=fars_id, cityId=tabriz_id),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("متعلق به استان", response.data["error"])

    def test_mismatched_id_and_supplied_name_are_rejected(self):
        tehran_id, tehran_city_id = location_ids("تهران", "تهران")
        response = self.client.post(
            "/api/auth/addresses",
            self.payload(provinceId=tehran_id, cityId=tehran_city_id),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("مطابقت ندارد", response.data["error"])

    def test_missing_and_unknown_location_values_are_rejected(self):
        missing = self.client.post(
            "/api/auth/addresses",
            self.payload(province="", city=""),
            format="json",
        )
        unknown = self.client.post(
            "/api/auth/addresses",
            self.payload(province="استان ساختگی"),
            format="json",
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertIn("استان", missing.data["error"])
        self.assertIn("معتبر نیست", unknown.data["error"])

    def test_edit_can_change_to_a_valid_pair_and_returns_ids(self):
        tehran_id, tehran_city_id = location_ids("تهران", "تهران")
        address = Address.objects.create(
            user=self.user,
            title="خانه",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="تهران",
            city="تهران",
            province_code=tehran_id,
            city_code=tehran_city_id,
            address="خیابان آزمایشی شماره ده",
        )
        fars_id, shiraz_id = location_ids("فارس", "شیراز")

        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            {
                "province": "فارس",
                "city": "شیراز",
                "provinceId": fars_id,
                "cityId": shiraz_id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        self.assertEqual(
            (address.province, address.city, address.province_code, address.city_code),
            ("فارس", "شیراز", fars_id, shiraz_id),
        )

    def test_edit_can_change_location_using_ids_only(self):
        address = Address.objects.create(
            user=self.user,
            title="خانه",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
        )
        fars_id, shiraz_id = location_ids("فارس", "شیراز")

        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            {"provinceId": fars_id, "cityId": shiraz_id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        self.assertEqual(
            (address.province, address.city, address.province_code, address.city_code),
            ("فارس", "شیراز", fars_id, shiraz_id),
        )

    def test_changing_only_province_rejects_the_now_incompatible_city(self):
        address = Address.objects.create(
            user=self.user,
            title="خانه",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
        )

        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            {"province": "فارس"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        address.refresh_from_db()
        self.assertEqual((address.province, address.city), ("تهران", "تهران"))

    def test_unrelated_partial_update_preserves_invalid_legacy_pair(self):
        address = Address.objects.create(
            user=self.user,
            title="قدیمی",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="legacy province",
            city="legacy city",
            address="خیابان آزمایشی شماره ده",
        )

        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            {"isDefault": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        self.assertEqual(
            (address.province, address.city, address.province_code, address.city_code),
            ("legacy province", "legacy city", None, None),
        )
        self.assertTrue(address.is_default)

    def test_full_edit_may_repeat_an_unchanged_invalid_legacy_pair(self):
        address = Address.objects.create(
            user=self.user,
            title="قدیمی",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="legacy province",
            city="legacy city",
            address="خیابان آزمایشی شماره ده",
        )
        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            self.payload(
                title="ویرایش شده",
                province=address.province,
                city=address.city,
            ),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        self.assertEqual(address.title, "ویرایش شده")
        self.assertEqual((address.province, address.city), ("legacy province", "legacy city"))

    def test_full_edit_backfills_codes_for_an_unchanged_valid_legacy_pair(self):
        address = Address.objects.create(
            user=self.user,
            title="قدیمی",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="فارس",
            city="شیراز",
            address="خیابان آزمایشی شماره ده",
        )

        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            self.payload(title="ویرایش شده"),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        address.refresh_from_db()
        expected_province_id, expected_city_id = location_ids("فارس", "شیراز")
        self.assertEqual(
            (address.province_code, address.city_code),
            (expected_province_id, expected_city_id),
        )

    def test_user_cannot_edit_another_users_address(self):
        address = Address.objects.create(
            user=self.other_user,
            title="خانه",
            full_name="کاربر دیگر",
            phone=self.other_user.phone,
            province="تهران",
            city="تهران",
            address="خیابان آزمایشی شماره ده",
        )

        response = self.client.patch(
            f"/api/auth/addresses/{address.id}",
            {"isDefault": True},
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        address.refresh_from_db()
        self.assertFalse(address.is_default)


class CheckoutLocationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(phone="09121234567")
        category = Category.objects.create(slug="tools", title="ابزار")
        self.product = Product.objects.create(
            title="بیل", category=category, price=100_000, stock=10
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def add_cart_item(self):
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, qty=1)

    def manual_payload(self, **changes):
        payload = {
            "fullName": "کاربر آزمایشی",
            "province": "فارس",
            "city": "شیراز",
            "address": "خیابان آزمایشی شماره ده",
            "postalCode": "7188812345",
        }
        payload.update(changes)
        return payload

    def test_manual_checkout_persists_validated_official_codes(self):
        self.add_cart_item()
        province_id, city_id = location_ids("فارس", "شیراز")

        response = self.client.post(
            "/api/orders",
            self.manual_payload(provinceId=province_id, cityId=city_id),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(user=self.user)
        self.assertEqual(
            (order.province, order.city, order.province_code, order.city_code),
            ("فارس", "شیراز", province_id, city_id),
        )

    def test_manual_checkout_rejects_invalid_pair_without_consuming_cart(self):
        self.add_cart_item()

        response = self.client.post(
            "/api/orders",
            self.manual_payload(city="تبریز"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("متعلق به استان", response.data["error"])
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.filter(cart__user=self.user).exists())

    def test_saved_legacy_address_checkout_remains_usable(self):
        self.add_cart_item()
        address = Address.objects.create(
            user=self.user,
            title="قدیمی",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="legacy province",
            city="legacy city",
            address="خیابان آزمایشی شماره ده",
        )

        response = self.client.post(
            "/api/orders", {"addressId": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(user=self.user)
        self.assertEqual((order.province, order.city), ("legacy province", "legacy city"))
        self.assertIsNone(order.province_code)
        self.assertIsNone(order.city_code)

    def test_saved_address_checkout_copies_codes_as_immutable_snapshot(self):
        self.add_cart_item()
        province_id, city_id = location_ids("فارس", "شیراز")
        address = Address.objects.create(
            user=self.user,
            title="خانه",
            full_name="کاربر آزمایشی",
            phone=self.user.phone,
            province="فارس",
            city="شیراز",
            province_code=province_id,
            city_code=city_id,
            address="خیابان آزمایشی شماره ده",
        )

        response = self.client.post(
            "/api/orders", {"addressId": address.id}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(user=self.user)
        self.assertEqual((order.province_code, order.city_code), (province_id, city_id))
