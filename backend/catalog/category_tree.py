from .models import Category


def visible_category_ids() -> set[int]:
    """Categories reachable through active nodes from an active root."""
    root_ids = set(
        Category.objects.filter(is_active=True, parents__isnull=True)
        .distinct()
        .values_list("id", flat=True)
    )
    visible = set(root_ids)
    frontier = root_ids

    while frontier:
        child_ids = set(
            Category.objects.filter(is_active=True, parents__id__in=frontier)
            .exclude(id__in=visible)
            .distinct()
            .values_list("id", flat=True)
        )
        visible.update(child_ids)
        frontier = child_ids

    return visible


def descendant_category_ids(
    category_id: int, *, allowed_ids: set[int] | None = None
) -> set[int]:
    """Return a category and every reachable descendant in the directed graph."""
    descendants = {category_id}
    frontier = {category_id}

    while frontier:
        queryset = Category.objects.filter(parents__id__in=frontier)
        if allowed_ids is not None:
            queryset = queryset.filter(id__in=allowed_ids)
        child_ids = set(
            queryset.exclude(id__in=descendants)
            .distinct()
            .values_list("id", flat=True)
        )
        descendants.update(child_ids)
        frontier = child_ids

    return descendants
