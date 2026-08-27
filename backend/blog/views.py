import math

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from common.responses import fail, ok
from common.search import SearchQueryTooLong

from .dto import category_dto, post_dto, tag_dto
from .models import BlogCategory, BlogPost, BlogTag
from .selectors import filter_posts, public_posts


class SuccessEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=True)
    data = serializers.JSONField()


class ErrorEnvelopeSerializer(serializers.Serializer):
    ok = serializers.BooleanField(default=False)
    error = serializers.CharField()


def pagination_values(request, *, default_per_page: int = 12):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        per_page = min(
            50,
            max(1, int(request.query_params.get("perPage", default_per_page))),
        )
        if page > 1_000_000:
            return None
    except (TypeError, ValueError):
        return None
    return page, per_page


class BlogPostListView(APIView):
    """فهرست عمومی نوشته‌های منتشرشده؛ پیش‌نویس‌ها هرگز وارد queryset نمی‌شوند."""

    authentication_classes: list = []

    @extend_schema(
        operation_id="blog_posts_list",
        parameters=[
            OpenApiParameter("category", str, description="نامک دسته‌بندی"),
            OpenApiParameter("tag", str, description="نامک برچسب"),
            OpenApiParameter("search", str, description="جستجو در عنوان، خلاصه و متن"),
            OpenApiParameter("page", int, description="شماره صفحه، از ۱"),
            OpenApiParameter("perPage", int, description="تعداد هر صفحه، حداکثر ۵۰"),
        ],
        responses={200: SuccessEnvelopeSerializer, 422: ErrorEnvelopeSerializer},
    )
    def get(self, request):
        pagination = pagination_values(request)
        if pagination is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        page, per_page = pagination
        try:
            queryset = filter_posts(
                public_posts(),
                category_slug=request.query_params.get("category", "").strip(),
                tag_slug=request.query_params.get("tag", "").strip(),
                search=request.query_params.get("search", ""),
            ).order_by("-published_at", "-created_at")
        except SearchQueryTooLong as exc:
            return fail(str(exc), 422)
        total = queryset.count()
        start = (page - 1) * per_page
        items = [post_dto(post) for post in queryset[start : start + per_page]]
        return ok(
            {
                "items": items,
                "total": total,
                "page": page,
                "perPage": per_page,
                "pages": math.ceil(total / per_page),
            }
        )


class BlogPostDetailView(APIView):
    authentication_classes: list = []

    @extend_schema(
        operation_id="blog_posts_retrieve",
        responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer}
    )
    def get(self, request, slug: str):
        post = public_posts().filter(slug=slug).first()
        if post is None:
            return fail("نوشته یافت نشد", 404)
        return ok({"post": post_dto(post, include_content=True)})


class BlogCategoryListView(APIView):
    authentication_classes: list = []

    @extend_schema(responses={200: SuccessEnvelopeSerializer})
    def get(self, request):
        categories = (
            BlogCategory.objects.annotate(
                published_count=Count(
                    "posts",
                    filter=Q(
                        posts__status=BlogPost.Status.PUBLISHED,
                        posts__published_at__isnull=False,
                        posts__published_at__lte=timezone.now(),
                    ),
                )
            )
            .filter(published_count__gt=0)
            .order_by("name")
        )
        return ok(
            {
                "categories": [
                    {**category_dto(category), "postsCount": category.published_count}
                    for category in categories
                ]
            }
        )


class BlogTagListView(APIView):
    authentication_classes: list = []

    @extend_schema(responses={200: SuccessEnvelopeSerializer})
    def get(self, request):
        tags = (
            BlogTag.objects.annotate(
                published_count=Count(
                    "posts",
                    filter=Q(
                        posts__status=BlogPost.Status.PUBLISHED,
                        posts__published_at__isnull=False,
                        posts__published_at__lte=timezone.now(),
                    ),
                )
            )
            .filter(published_count__gt=0)
            .order_by("name")
        )
        return ok(
            {
                "tags": [
                    {**tag_dto(tag), "postsCount": tag.published_count} for tag in tags
                ]
            }
        )
