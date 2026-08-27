from django.db.models import QuerySet

from common.search import filter_by_search

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
        )
    return queryset.distinct()
