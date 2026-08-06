from django.db.models import Q, QuerySet

from .models import BlogPost


def post_queryset() -> QuerySet[BlogPost]:
    return BlogPost.objects.select_related("author", "category").prefetch_related(
        "tags"
    )


def public_posts() -> QuerySet[BlogPost]:
    return post_queryset().published()


def filter_posts(
    queryset: QuerySet[BlogPost],
    *,
    category_slug: str = "",
    tag_slug: str = "",
    search: str = "",
) -> QuerySet[BlogPost]:
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    if tag_slug:
        queryset = queryset.filter(tags__slug=tag_slug)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(excerpt__icontains=search)
            | Q(content__icontains=search)
        )
    return queryset.distinct()
