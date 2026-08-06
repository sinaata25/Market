from rest_framework import serializers

from .models import BlogCategory, BlogPost, BlogTag


class BlogPostWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    slug = serializers.CharField(
        max_length=280, required=False, allow_blank=True, default=""
    )
    excerpt = serializers.CharField(max_length=500)
    content = serializers.CharField()
    categorySlug = serializers.CharField(
        max_length=120, required=False, allow_blank=True, allow_null=True
    )
    tagSlugs = serializers.ListField(
        child=serializers.CharField(max_length=80), required=False, default=list
    )
    status = serializers.ChoiceField(choices=BlogPost.Status.choices)
    publishedAt = serializers.DateTimeField(required=False, allow_null=True)
    seoTitle = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )
    seoDescription = serializers.CharField(
        max_length=320, required=False, allow_blank=True, default=""
    )

    def validate_slug(self, value):
        value = value.strip().strip("/")
        if value and any(character.isspace() for character in value):
            raise serializers.ValidationError("نامک نباید فاصله داشته باشد")
        return value

    def validate_categorySlug(self, value):
        if not value:
            return None
        category = BlogCategory.objects.filter(slug=value).first()
        if category is None:
            raise serializers.ValidationError("دسته‌بندی وبلاگ یافت نشد")
        return category

    def validate_tagSlugs(self, values):
        unique_values = list(dict.fromkeys(values))
        tags = list(BlogTag.objects.filter(slug__in=unique_values))
        if len(tags) != len(unique_values):
            raise serializers.ValidationError("یک یا چند برچسب یافت نشد")
        tag_by_slug = {tag.slug: tag for tag in tags}
        return [tag_by_slug[slug] for slug in unique_values]

    def validate(self, data):
        instance = self.context.get("instance")
        status = data.get("status", getattr(instance, "status", BlogPost.Status.DRAFT))
        published_at = data.get(
            "publishedAt", getattr(instance, "published_at", None)
        )
        if status == BlogPost.Status.PUBLISHED and published_at is None:
            raise serializers.ValidationError(
                {"publishedAt": "نوشته منتشرشده باید زمان انتشار داشته باشد"}
            )
        if status == BlogPost.Status.DRAFT and published_at is not None:
            raise serializers.ValidationError(
                {"publishedAt": "پیش‌نویس نباید زمان انتشار داشته باشد"}
            )
        return data


class TaxonomyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    slug = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_slug(self, value):
        value = value.strip().strip("/")
        if value and any(character.isspace() for character in value):
            raise serializers.ValidationError("نامک نباید فاصله داشته باشد")
        return value


class TagWriteSerializer(TaxonomyWriteSerializer):
    name = serializers.CharField(max_length=60)
    slug = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
