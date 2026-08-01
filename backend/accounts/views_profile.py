"""پروفایل کاربر: اطلاعات شخصی، آدرس‌ها، علاقه‌مندی‌ها، خلاصه فعالیت"""

from django.db.models import Avg, Count, Sum
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from catalog.dto import product_dto
from catalog.models import Product, Review
from common.responses import fail, ok
from common.utils import is_valid_iran_mobile, normalize_phone
from orders.models import Order

from .models import Address, Favorite


class AuthRequired:
    permission_classes = [IsAuthenticated]


def address_dto(a: Address) -> dict:
    return {
        "id": a.id,
        "title": a.title,
        "fullName": a.full_name,
        "phone": a.phone,
        "province": a.province,
        "city": a.city,
        "address": a.address,
        "postalCode": a.postal_code,
        "isDefault": a.is_default,
    }


# ─── اطلاعات شخصی ────────────────────────────────────────────


class ProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, allow_blank=True, default="")


class ProfileView(AuthRequired, APIView):
    """خلاصه پروفایل + آمار فعالیت کاربر"""

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user)
        paid = orders.exclude(status=Order.Status.CANCELED)

        return ok(
            {
                "user": {
                    "id": user.id,
                    "phone": user.phone,
                    "name": user.name or None,
                    "isStaff": user.is_staff,
                    "isSeoManager": user.is_seo_manager,
                    "dateJoined": user.date_joined.isoformat(),
                },
                "stats": {
                    "ordersCount": orders.count(),
                    "pendingCount": orders.filter(
                        status=Order.Status.PENDING
                    ).count(),
                    "deliveredCount": orders.filter(
                        status=Order.Status.DELIVERED
                    ).count(),
                    "totalSpent": paid.aggregate(s=Sum("total_price"))["s"] or 0,
                    "addressesCount": user.addresses.count(),
                    "favoritesCount": user.favorites.count(),
                    "reviewsCount": Review.objects.filter(user=user).count(),
                },
            }
        )

    def patch(self, request):
        ser = ProfileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = request.user
        user.name = ser.validated_data["name"].strip()
        user.save(update_fields=["name"])
        return ok(
            {
                "user": {
                    "id": user.id,
                    "phone": user.phone,
                    "name": user.name or None,
                }
            }
        )


# ─── آدرس‌ها ─────────────────────────────────────────────────


class AddressSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50, default="خانه")
    fullName = serializers.CharField(
        min_length=3,
        max_length=100,
        error_messages={
            "required": "نام تحویل‌گیرنده الزامی است",
            "min_length": "نام تحویل‌گیرنده حداقل ۳ حرف باشد",
        },
    )
    phone = serializers.CharField(
        error_messages={"required": "شماره تماس الزامی است"}
    )
    province = serializers.CharField(
        min_length=2, error_messages={"required": "استان الزامی است"}
    )
    city = serializers.CharField(
        min_length=2, error_messages={"required": "شهر الزامی است"}
    )
    address = serializers.CharField(
        min_length=10,
        error_messages={
            "required": "آدرس الزامی است",
            "min_length": "آدرس کامل‌تری وارد کنید",
        },
    )
    postalCode = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    isDefault = serializers.BooleanField(default=False)

    def validate_phone(self, v):
        phone = normalize_phone(v)
        if not is_valid_iran_mobile(phone):
            raise serializers.ValidationError("شماره تماس معتبر نیست")
        return phone

    def validate_postalCode(self, v):
        code = normalize_phone(v)
        if code and len(code) != 10:
            raise serializers.ValidationError("کد پستی باید ۱۰ رقم باشد")
        return code


def apply_address(addr: Address, data: dict, user) -> Address:
    addr.user = user
    addr.title = data["title"]
    addr.full_name = data["fullName"]
    addr.phone = data["phone"]
    addr.province = data["province"]
    addr.city = data["city"]
    addr.address = data["address"]
    addr.postal_code = data["postalCode"]
    addr.is_default = data["isDefault"]
    addr.save()
    # فقط یک آدرس می‌تواند پیش‌فرض باشد
    if addr.is_default:
        Address.objects.filter(user=user).exclude(pk=addr.pk).update(
            is_default=False
        )
    return addr


class AddressListView(AuthRequired, APIView):
    def get(self, request):
        return ok(
            {
                "addresses": [
                    address_dto(a) for a in request.user.addresses.all()
                ]
            }
        )

    def post(self, request):
        ser = AddressSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        # اولین آدرس کاربر خودکار پیش‌فرض می‌شود
        if not request.user.addresses.exists():
            d["isDefault"] = True
        addr = apply_address(Address(), d, request.user)
        return ok({"address": address_dto(addr)}, status=201)


class AddressDetailView(AuthRequired, APIView):
    def _get(self, request, pk):
        return Address.objects.filter(pk=pk, user=request.user).first()

    def patch(self, request, pk: int):
        addr = self._get(request, pk)
        if addr is None:
            return fail("آدرس یافت نشد", 404)
        ser = AddressSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        addr = apply_address(addr, ser.validated_data, request.user)
        return ok({"address": address_dto(addr)})

    def delete(self, request, pk: int):
        addr = self._get(request, pk)
        if addr is None:
            return fail("آدرس یافت نشد", 404)
        was_default = addr.is_default
        addr.delete()
        # آدرس پیش‌فرض بعدی
        if was_default:
            nxt = request.user.addresses.first()
            if nxt:
                nxt.is_default = True
                nxt.save(update_fields=["is_default"])
        return ok({"deleted": True})


# ─── علاقه‌مندی‌ها ───────────────────────────────────────────


class FavoriteListView(AuthRequired, APIView):
    def get(self, request):
        favorites = request.user.favorites.select_related(
            "product__category"
        ).prefetch_related("product__images")
        return ok(
            {"favorites": [product_dto(f.product) for f in favorites]}
        )

    def post(self, request):
        product_id = request.data.get("productId")
        product = Product.objects.filter(pk=product_id).first()
        if product is None:
            return fail("محصول یافت نشد", 404)
        fav, created = Favorite.objects.get_or_create(
            user=request.user, product=product
        )
        if not created:
            fav.delete()
            return ok({"favorited": False})
        return ok({"favorited": True}, status=201)


class FavoriteCheckView(AuthRequired, APIView):
    """بررسی وضعیت علاقه‌مندی یک محصول"""

    def get(self, request, pk: int):
        exists = Favorite.objects.filter(
            user=request.user, product_id=pk
        ).exists()
        return ok({"favorited": exists})


# ─── دیدگاه‌های من ───────────────────────────────────────────


class MyReviewsView(AuthRequired, APIView):
    def get(self, request):
        reviews = Review.objects.filter(user=request.user).select_related(
            "product"
        )
        return ok(
            {
                "reviews": [
                    {
                        "id": r.id,
                        "rating": r.rating,
                        "text": r.text,
                        "createdAt": r.created_at.isoformat(),
                        "productId": r.product_id,
                        "productTitle": r.product.title,
                        "productEmoji": r.product.emoji,
                    }
                    for r in reviews
                ]
            }
        )

    def delete(self, request):
        review_id = request.data.get("reviewId")
        review = Review.objects.filter(pk=review_id, user=request.user).first()
        if review is None:
            return fail("دیدگاه یافت نشد", 404)
        product_id = review.product_id
        review.delete()
        aggregate = Review.objects.filter(product_id=product_id).aggregate(
            avg=Avg("rating"), count=Count("id")
        )
        Product.objects.filter(pk=product_id).update(
            rating=round(aggregate["avg"] or 0, 1),
            rating_count=aggregate["count"],
        )
        return ok({"deleted": True})
