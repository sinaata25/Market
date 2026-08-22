"""Shared DRF validation for address and checkout location fields."""

from __future__ import annotations

from rest_framework import serializers

from .registry import (
    CityProvinceMismatch,
    UnknownCity,
    UnknownProvince,
    location_names_match,
    resolve_location_ids,
    resolve_location_names,
)


LOCATION_FIELDS = {"province", "city", "provinceId", "cityId"}


def validate_location_fields(
    data: dict,
    *,
    existing=None,
    required: bool = True,
) -> dict:
    """Validate/canonicalize a province/city pair without breaking legacy rows.

    `existing` may be an Address-like object with string names and optional
    `province_code`/`city_code` attributes. If a partial update does not touch a
    location field, or repeats an unchanged legacy pair, that historic value is
    preserved. Any new or changed pair is validated against the current dataset.
    """

    touched = bool(LOCATION_FIELDS.intersection(data))
    if existing is not None and not touched:
        return data

    existing_province = getattr(existing, "province", None)
    existing_city = getattr(existing, "city", None)
    province_name = data.get("province", existing_province)
    city_name = data.get("city", existing_city)

    province_id = data.get("provinceId")
    city_id = data.get("cityId")
    ids_supplied = bool(province_id or city_id)
    if ids_supplied and not province_id:
        raise serializers.ValidationError(
            {"provinceId": "شناسه استان الزامی است"}
        )
    if ids_supplied and not city_id:
        raise serializers.ValidationError({"cityId": "شناسه شهر الزامی است"})

    if ids_supplied:
        try:
            resolved = resolve_location_ids(province_id, city_id)
        except UnknownProvince as exc:
            raise serializers.ValidationError(
                {"provinceId": "استان انتخاب شده معتبر نیست"}
            ) from exc
        except UnknownCity as exc:
            raise serializers.ValidationError(
                {"cityId": "شهر انتخاب شده معتبر نیست"}
            ) from exc
        except CityProvinceMismatch as exc:
            raise serializers.ValidationError(
                {"cityId": "شهر انتخاب شده متعلق به استان انتخاب شده نیست"}
            ) from exc

        supplied_province_name = data.get("province")
        supplied_city_name = data.get("city")
        if supplied_province_name and not location_names_match(
            supplied_province_name, resolved.province_name
        ):
            raise serializers.ValidationError(
                {"province": "شناسه استان با نام استان مطابقت ندارد"}
            )
        if supplied_city_name and not location_names_match(
            supplied_city_name, resolved.city_name
        ):
            raise serializers.ValidationError(
                {"city": "شناسه شهر با نام شهر مطابقت ندارد"}
            )
    else:
        if required and not province_name:
            raise serializers.ValidationError({"province": "استان الزامی است"})
        if required and not city_name:
            raise serializers.ValidationError({"city": "شهر الزامی است"})
        if not province_name or not city_name:
            return data

        unchanged_legacy_pair = (
            existing is not None
            and data.get("province", existing_province) == existing_province
            and data.get("city", existing_city) == existing_city
        )
        existing_province_id = getattr(existing, "province_code", None)
        existing_city_id = getattr(existing, "city_code", None)
        if unchanged_legacy_pair and existing_province_id and existing_city_id:
            data["province"] = existing_province
            data["city"] = existing_city
            data["provinceId"] = existing_province_id
            data["cityId"] = existing_city_id
            return data

        try:
            resolved = resolve_location_names(province_name, city_name)
        except (UnknownProvince, UnknownCity, CityProvinceMismatch) as exc:
            if unchanged_legacy_pair:
                data["province"] = existing_province
                data["city"] = existing_city
                data["provinceId"] = existing_province_id
                data["cityId"] = existing_city_id
                return data
            if isinstance(exc, UnknownProvince):
                detail = {"province": "استان انتخاب شده معتبر نیست"}
            elif isinstance(exc, UnknownCity):
                detail = {"city": "شهر انتخاب شده معتبر نیست"}
            else:
                detail = {
                    "city": "شهر انتخاب شده متعلق به استان انتخاب شده نیست"
                }
            raise serializers.ValidationError(detail) from exc

    data["province"] = resolved.province_name
    data["city"] = resolved.city_name
    data["provinceId"] = resolved.province_id
    data["cityId"] = resolved.city_id
    return data
