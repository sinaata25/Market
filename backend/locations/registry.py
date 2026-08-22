"""In-process access to the versioned Iranian province/city reference data."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parent / "data" / "iran_provinces_cities_1404.json"

_CHARACTER_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "أ": "ا",
        "إ": "ا",
        "ة": "ه",
        "ۀ": "ه",
        "ـ": None,
    }
)


class LocationError(ValueError):
    """Base class for controlled location lookup failures."""


class UnknownProvince(LocationError):
    pass


class UnknownCity(LocationError):
    pass


class CityProvinceMismatch(LocationError):
    pass


@dataclass(frozen=True, slots=True)
class City:
    id: str
    name: str
    county_name: str
    province_id: str


@dataclass(frozen=True, slots=True)
class Province:
    id: str
    name: str
    cities: tuple[City, ...]


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    province_id: str
    province_name: str
    city_id: str | None
    city_name: str


@dataclass(frozen=True, slots=True)
class LocationRegistry:
    year: int
    provinces: tuple[Province, ...]
    provinces_by_id: dict[str, Province]
    provinces_by_name: dict[str, Province]
    cities_by_id: dict[str, City]
    cities_by_name: dict[str, tuple[City, ...]]
    province_cities_by_name: dict[str, dict[str, tuple[City, ...]]]


def normalize_location_name(value: str) -> str:
    """Normalize harmless Arabic/Persian spelling differences for comparisons."""

    text = unicodedata.normalize("NFKC", str(value)).translate(
        _CHARACTER_TRANSLATION
    )
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return " ".join(text.split())


def location_names_match(first: str, second: str) -> bool:
    return normalize_location_name(first) == normalize_location_name(second)


@lru_cache(maxsize=1)
def get_registry() -> LocationRegistry:
    document = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    metadata = document["metadata"]

    provinces: list[Province] = []
    province_ids: set[str] = set()
    city_ids: set[str] = set()
    for province_data in document["provinces"]:
        province_id = province_data["id"]
        if province_id in province_ids:
            raise RuntimeError(f"Duplicate province code in location data: {province_id}")
        province_ids.add(province_id)

        cities: list[City] = []
        for city_data in province_data["cities"]:
            city_id = city_data["id"]
            if city_id in city_ids:
                raise RuntimeError(f"Duplicate city code in location data: {city_id}")
            city_ids.add(city_id)
            cities.append(
                City(
                    id=city_id,
                    name=city_data["name"],
                    county_name=city_data["county"],
                    province_id=province_id,
                )
            )
        provinces.append(
            Province(
                id=province_id,
                name=province_data["name"],
                cities=tuple(cities),
            )
        )

    if len(provinces) != metadata["provinceCount"]:
        raise RuntimeError("Iranian province dataset count does not match metadata")
    if len(city_ids) != metadata["cityCount"]:
        raise RuntimeError("Iranian city dataset count does not match metadata")

    provinces_tuple = tuple(provinces)
    provinces_by_id = {province.id: province for province in provinces_tuple}
    provinces_by_name = {
        normalize_location_name(province.name): province
        for province in provinces_tuple
    }
    if len(provinces_by_name) != len(provinces_tuple):
        raise RuntimeError("Iranian province names are not unique after normalization")

    cities_by_id: dict[str, City] = {}
    cities_by_name_lists: dict[str, list[City]] = {}
    province_cities_by_name: dict[str, dict[str, tuple[City, ...]]] = {}
    for province in provinces_tuple:
        province_city_lists: dict[str, list[City]] = {}
        for city in province.cities:
            cities_by_id[city.id] = city
            key = normalize_location_name(city.name)
            cities_by_name_lists.setdefault(key, []).append(city)
            province_city_lists.setdefault(key, []).append(city)
        province_cities_by_name[province.id] = {
            key: tuple(matches) for key, matches in province_city_lists.items()
        }

    return LocationRegistry(
        year=metadata["year"],
        provinces=provinces_tuple,
        provinces_by_id=provinces_by_id,
        provinces_by_name=provinces_by_name,
        cities_by_id=cities_by_id,
        cities_by_name={
            key: tuple(matches) for key, matches in cities_by_name_lists.items()
        },
        province_cities_by_name=province_cities_by_name,
    )


def get_province_by_id(province_id: str) -> Province:
    province = get_registry().provinces_by_id.get(str(province_id).strip())
    if province is None:
        raise UnknownProvince
    return province


def resolve_location_ids(province_id: str, city_id: str) -> ResolvedLocation:
    registry = get_registry()
    province = registry.provinces_by_id.get(str(province_id).strip())
    if province is None:
        raise UnknownProvince
    city = registry.cities_by_id.get(str(city_id).strip())
    if city is None:
        raise UnknownCity
    if city.province_id != province.id:
        raise CityProvinceMismatch
    return ResolvedLocation(
        province_id=province.id,
        province_name=province.name,
        city_id=city.id,
        city_name=city.name,
    )


def resolve_location_names(province_name: str, city_name: str) -> ResolvedLocation:
    registry = get_registry()
    province = registry.provinces_by_name.get(
        normalize_location_name(province_name)
    )
    if province is None:
        raise UnknownProvince

    city_key = normalize_location_name(city_name)
    matches = registry.province_cities_by_name[province.id].get(city_key)
    if not matches:
        if city_key in registry.cities_by_name:
            raise CityProvinceMismatch
        raise UnknownCity

    # Three official 1404 city names are duplicated within their province. A
    # name-only legacy request is valid but cannot identify which official code
    # was meant; only ID-aware clients receive a persisted city code.
    city_id = matches[0].id if len(matches) == 1 else None
    return ResolvedLocation(
        province_id=province.id,
        province_name=province.name,
        city_id=city_id,
        city_name=matches[0].name,
    )
