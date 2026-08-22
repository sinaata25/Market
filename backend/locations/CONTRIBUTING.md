# Locations app contributor guide

## Responsibility

`locations` owns the versioned Iranian province/city reference dataset, public
lookup endpoints, and the shared address/checkout validation boundary. It has
no database tables: reference data changes only through a reviewed application
deployment.

## Dataset

The compact JSON under `data/` is derived from the Statistical Centre annual
geographic file as documented in `data/README.md`. Keep the official codes as
strings because leading zeroes are significant. Only `DivisionType = 5` records
are selectable cities; urban zones (`DivisionType = 7`) must not be mixed in.

The 1404 source contains 31 provinces and 1,481 cities. Three province/name
pairs are duplicated, so city IDs and county names must not be dropped from API
responses. Name-only legacy submissions can validate those pairs but cannot
identify which official city code was selected.

## API and validation

- `GET /api/locations/provinces`
- `GET /api/locations/provinces/<official-code>/cities`

Both endpoints are public, slashless, sorted by display name, and cacheable for
one day. Address and manual-checkout requests may use the official
`provinceId`/`cityId` pair or the backward-compatible `province`/`city` names.
IDs are authoritative when present; supplied names must agree with them.

Do not reject unchanged historic Address strings on unrelated PATCH operations,
and do not reject checkout by an owned saved legacy address. New or changed
location pairs must always pass `validate_location_fields()`.
