import math

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from accounts.permissions import ShopAdminRequiredMixin
from common.responses import fail, ok
from common.search import SearchQueryTooLong, filter_by_search

from .dto import category_dto, post_dto, tag_dto
from .models import BlogCategory, BlogPost, BlogTag
from .selectors import post_queryset
from .serializers import BlogPostWriteSerializer, TagWriteSerializer, TaxonomyWriteSerializer
from .services import (
    delete_post,
    publish_post,
    remove_featured_image,
    replace_featured_image,
    save_category,
    save_post,
    save_tag,
    unpublish_post,
)
from .validators import validate_featured_image
from .views import ErrorEnvelopeSerializer, SuccessEnvelopeSerializer, pagination_values


class PublishSerializer(serializers.Serializer):
    publishedAt = serializers.DateTimeField(required=False, allow_null=True)


def get_post(pk: int) -> BlogPost | None:
    return post_queryset().filter(pk=pk).first()


class AdminBlogPostListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        operation_id="admin_blog_posts_list",
        parameters=[
            OpenApiParameter("status", str, enum=list(BlogPost.Status.values)),
            OpenApiParameter("search", str),
            OpenApiParameter("page", int),
        ],
        responses={
            200: SuccessEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
            422: ErrorEnvelopeSerializer,
        },
    )
    def get(self, request):
        pagination = pagination_values(request, default_per_page=15)
        if pagination is None:
            return fail("پارامتر صفحه‌بندی نامعتبر است", 422)
        page, per_page = pagination
        queryset = post_queryset().order_by("-created_at")
        status = request.query_params.get("status", "")
        if status in BlogPost.Status.values:
            queryset = queryset.filter(status=status)
        search = request.query_params.get("search", "")
        if search:
            try:
                queryset = filter_by_search(
                    queryset,
                    search,
                    fields=(
                        "title",
                        "slug",
                        "excerpt",
                        "content",
                        "category__name",
                        "tags__name",
                    ),
                ).distinct()
            except SearchQueryTooLong as exc:
                return fail(str(exc), 422)
        total = queryset.count()
        start = (page - 1) * per_page
        posts = [
            post_dto(post, include_admin=True)
            for post in queryset[start : start + per_page]
        ]
        return ok(
            {
                "posts": posts,
                "total": total,
                "page": page,
                "pages": math.ceil(total / per_page) or 1,
            }
        )

    @extend_schema(
        operation_id="admin_blog_posts_create",
        request=BlogPostWriteSerializer,
        responses={
            201: SuccessEnvelopeSerializer,
            400: ErrorEnvelopeSerializer,
            403: ErrorEnvelopeSerializer,
        },
    )
    def post(self, request):
        serializer = BlogPostWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = save_post(
            post=BlogPost(), data=dict(serializer.validated_data), author=request.user
        )
        post = get_post(post.pk)
        return ok(
            {"post": post_dto(post, include_content=True, include_admin=True)},
            status=201,
        )


class AdminBlogPostDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        operation_id="admin_blog_posts_retrieve",
        responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer},
    )
    def get(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        return ok({"post": post_dto(post, include_content=True, include_admin=True)})

    @extend_schema(
        operation_id="admin_blog_posts_update",
        request=BlogPostWriteSerializer,
        responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer},
    )
    def patch(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        serializer = BlogPostWriteSerializer(
            data=request.data,
            partial=True,
            context={"instance": post},
        )
        serializer.is_valid(raise_exception=True)
        post = save_post(post=post, data=dict(serializer.validated_data))
        post = get_post(post.pk)
        return ok({"post": post_dto(post, include_content=True, include_admin=True)})

    @extend_schema(
        operation_id="admin_blog_posts_delete",
        responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer},
    )
    def delete(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        delete_post(post)
        return ok({"deleted": True})


class AdminBlogPublishView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request=PublishSerializer,
        responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer},
    )
    def post(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        serializer = PublishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publish_post(post, serializer.validated_data.get("publishedAt"))
        return ok({"post": post_dto(get_post(pk), include_admin=True)})


class AdminBlogUnpublishView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=None, responses={200: SuccessEnvelopeSerializer})
    def post(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        unpublish_post(post)
        return ok({"post": post_dto(get_post(pk), include_admin=True)})


class AdminBlogFeaturedImageView(ShopAdminRequiredMixin, APIView):
    @extend_schema(
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}, "required": ["file"]}},
        responses={201: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer, 422: ErrorEnvelopeSerializer},
    )
    def post(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        image = request.FILES.get("file")
        if image is None:
            return fail("فایل تصویر ارسال نشده است", 422)
        try:
            validate_featured_image(image)
        except DjangoValidationError as exc:
            messages = getattr(exc, "messages", None)
            return fail(messages[0] if messages else "تصویر معتبر نیست", 422)
        replace_featured_image(post, image)
        return ok(
            {"post": post_dto(get_post(pk), include_content=True, include_admin=True)},
            status=201,
        )

    @extend_schema(responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer})
    def delete(self, request, pk: int):
        post = get_post(pk)
        if post is None:
            return fail("نوشته یافت نشد", 404)
        remove_featured_image(post)
        return ok({"post": post_dto(get_post(pk), include_admin=True)})


class AdminBlogCategoryListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: SuccessEnvelopeSerializer})
    def get(self, request):
        return ok({"categories": [category_dto(item) for item in BlogCategory.objects.all()]})

    @extend_schema(request=TaxonomyWriteSerializer, responses={201: SuccessEnvelopeSerializer})
    def post(self, request):
        serializer = TaxonomyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = save_category(BlogCategory(), dict(serializer.validated_data))
        return ok({"category": category_dto(category)}, status=201)


class AdminBlogCategoryDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=TaxonomyWriteSerializer, responses={200: SuccessEnvelopeSerializer})
    def patch(self, request, pk: int):
        category = BlogCategory.objects.filter(pk=pk).first()
        if category is None:
            return fail("دسته‌بندی یافت نشد", 404)
        serializer = TaxonomyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_category(category, dict(serializer.validated_data))
        return ok({"category": category_dto(category)})

    @extend_schema(responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer})
    def delete(self, request, pk: int):
        category = BlogCategory.objects.filter(pk=pk).first()
        if category is None:
            return fail("دسته‌بندی یافت نشد", 404)
        category.delete()
        return ok({"deleted": True})


class AdminBlogTagListView(ShopAdminRequiredMixin, APIView):
    @extend_schema(responses={200: SuccessEnvelopeSerializer})
    def get(self, request):
        return ok({"tags": [tag_dto(item) for item in BlogTag.objects.all()]})

    @extend_schema(request=TagWriteSerializer, responses={201: SuccessEnvelopeSerializer})
    def post(self, request):
        serializer = TagWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = save_tag(BlogTag(), dict(serializer.validated_data))
        return ok({"tag": tag_dto(tag)}, status=201)


class AdminBlogTagDetailView(ShopAdminRequiredMixin, APIView):
    @extend_schema(request=TagWriteSerializer, responses={200: SuccessEnvelopeSerializer})
    def patch(self, request, pk: int):
        tag = BlogTag.objects.filter(pk=pk).first()
        if tag is None:
            return fail("برچسب یافت نشد", 404)
        serializer = TagWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_tag(tag, dict(serializer.validated_data))
        return ok({"tag": tag_dto(tag)})

    @extend_schema(responses={200: SuccessEnvelopeSerializer, 404: ErrorEnvelopeSerializer})
    def delete(self, request, pk: int):
        tag = BlogTag.objects.filter(pk=pk).first()
        if tag is None:
            return fail("برچسب یافت نشد", 404)
        tag.delete()
        return ok({"deleted": True})
