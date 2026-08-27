"""Reusable Django-admin behavior."""

from common.search import SearchQueryTooLong, search_query_variants


class NormalizedSearchAdminMixin:
    """Make built-in admin search tolerant of Persian/Arabic variants."""

    def get_search_results(self, request, queryset, search_term):
        try:
            variants = search_query_variants(search_term)
        except SearchQueryTooLong:
            return queryset.none(), False
        if not variants:
            return super().get_search_results(request, queryset, search_term)

        combined = queryset.none()
        may_have_duplicates = False
        for variant in variants:
            results, duplicates = super().get_search_results(
                request, queryset, variant
            )
            combined = combined | results
            may_have_duplicates = may_have_duplicates or duplicates
        return combined, may_have_duplicates
