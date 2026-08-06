from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from .models import BlogCategory, BlogPost, BlogTag


FIELD_MAP = {
    "title": "title",
    "slug": "slug",
    "excerpt": "excerpt",
    "content": "content",
    "categorySlug": "category",
    "status": "status",
    "publishedAt": "published_at",
    "seoTitle": "seo_title",
    "seoDescription": "seo_description",
}


def _validation_detail(exc: DjangoValidationError):
    return exc.message_dict if hasattr(exc, "message_dict") else exc.messages


def _save_model(instance) -> None:
    try:
        instance.save()
    except DjangoValidationError as exc:
        raise serializers.ValidationError(_validation_detail(exc)) from exc
    except IntegrityError as exc:
        raise serializers.ValidationError("نام یا نامک تکراری است") from exc


def save_post(*, post: BlogPost, data: dict, author=None) -> BlogPost:
    tags = data.pop("tagSlugs", None)
    generated_slug = "slug" in data and not data["slug"]
    for api_field, model_field in FIELD_MAP.items():
        if api_field in data:
            setattr(post, model_field, data[api_field])
    if author is not None:
        post.author = author

    attempts = 3 if generated_slug else 1
    for attempt in range(attempts):
        try:
            with transaction.atomic():
                post.save()
            break
        except DjangoValidationError as exc:
            raise serializers.ValidationError(_validation_detail(exc)) from exc
        except IntegrityError as exc:
            if attempt + 1 >= attempts:
                raise serializers.ValidationError("نامک تکراری است") from exc
            post.slug = ""
    if tags is not None:
        post.tags.set(tags)
    return post


def publish_post(post: BlogPost, published_at=None) -> BlogPost:
    post.status = BlogPost.Status.PUBLISHED
    post.published_at = published_at or timezone.now()
    _save_model(post)
    return post


def unpublish_post(post: BlogPost) -> BlogPost:
    post.status = BlogPost.Status.DRAFT
    post.published_at = None
    _save_model(post)
    return post


def replace_featured_image(post: BlogPost, image) -> BlogPost:
    old_name = post.featured_image.name if post.featured_image else ""
    old_storage = post.featured_image.storage if post.featured_image else None
    post.featured_image = image
    _save_model(post)
    if old_name and old_storage:
        transaction.on_commit(lambda: old_storage.delete(old_name))
    return post


def remove_featured_image(post: BlogPost) -> BlogPost:
    if not post.featured_image:
        return post
    name = post.featured_image.name
    storage = post.featured_image.storage
    post.featured_image = None
    _save_model(post)
    transaction.on_commit(lambda: storage.delete(name))
    return post


def delete_post(post: BlogPost) -> None:
    name = post.featured_image.name if post.featured_image else ""
    storage = post.featured_image.storage if post.featured_image else None
    post.delete()
    if name and storage:
        transaction.on_commit(lambda: storage.delete(name))


def save_category(category: BlogCategory, data: dict) -> BlogCategory:
    category.name = data["name"]
    category.slug = data.get("slug", "")
    category.description = data.get("description", "")
    _save_model(category)
    return category


def save_tag(tag: BlogTag, data: dict) -> BlogTag:
    tag.name = data["name"]
    tag.slug = data.get("slug", "")
    _save_model(tag)
    return tag
