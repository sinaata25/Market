"""Shared, database-backed text-search normalization helpers."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from django.db.models import F, Q, QuerySet, TextField, Value
from django.db.models.functions import Lower, Replace


MAX_SEARCH_LENGTH = 200
_SPACE_RE = re.compile(r"\s+")
_QUERY_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
    }
)
_DATABASE_REPLACEMENTS = (
    ("ي", "ی"),
    ("ى", "ی"),
    ("ك", "ک"),
    ("\u00a0", " "),
    ("\u200c", " "),
    ("٠", "0"),
    ("١", "1"),
    ("٢", "2"),
    ("٣", "3"),
    ("٤", "4"),
    ("٥", "5"),
    ("٦", "6"),
    ("٧", "7"),
    ("٨", "8"),
    ("٩", "9"),
    ("۰", "0"),
    ("۱", "1"),
    ("۲", "2"),
    ("۳", "3"),
    ("۴", "4"),
    ("۵", "5"),
    ("۶", "6"),
    ("۷", "7"),
    ("۸", "8"),
    ("۹", "9"),
)


class SearchQueryTooLong(ValueError):
    pass


def normalize_search_text(value: object, *, max_length: int = MAX_SEARCH_LENGTH) -> str:
    """Canonicalize query text without changing stored model data."""

    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.translate(_QUERY_TRANSLATION)
    text = text.replace("\u00a0", " ").replace("\u200c", " ")
    text = _SPACE_RE.sub(" ", text).strip().lower()
    if len(text) > max_length:
        raise SearchQueryTooLong(
            f"عبارت جستجو حداکثر {max_length} نویسه می‌تواند باشد"
        )
    return text


def search_query_variants(value: object) -> tuple[str, ...]:
    """Return Persian/Arabic keyboard variants for Django-admin search."""

    normalized = normalize_search_text(value)
    if not normalized:
        return ()
    arabic = normalized.translate(str.maketrans({"ی": "ي", "ک": "ك"}))
    return tuple(dict.fromkeys((normalized, arabic)))


def _normalized_database_field(field_name: str):
    expression = F(field_name)
    for source, replacement in _DATABASE_REPLACEMENTS:
        expression = Replace(
            expression,
            Value(source),
            Value(replacement),
            output_field=TextField(),
        )
    return Lower(expression)


def filter_by_search(
    queryset: QuerySet,
    value: object,
    *,
    fields: Sequence[str],
    include_pk: bool = False,
) -> QuerySet:
    """Require every query token to occur in one of the allowed text fields.

    Fields are normalized in SQL, so Arabic/Persian letter and digit variants match
    without loading rows into Python. Callers searching through multi-valued joins
    should add ``distinct()`` after this helper.
    """

    search = normalize_search_text(value)
    if not search:
        return queryset

    annotations = {
        f"_normalized_search_{index}": _normalized_database_field(field_name)
        for index, field_name in enumerate(fields)
    }
    matched_queryset = queryset.annotate(**annotations)

    condition = Q()
    for token in search.split(" "):
        token_condition = Q()
        for alias in annotations:
            token_condition |= Q(**{f"{alias}__contains": token})
        condition &= token_condition

    if include_pk and search.isascii() and search.isdecimal() and len(search) <= 18:
        condition |= Q(pk=int(search))
    matching_ids = (
        matched_queryset.filter(condition).order_by().values("pk").distinct()
    )
    return queryset.filter(pk__in=matching_ids)
