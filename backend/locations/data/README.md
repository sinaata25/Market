# Iranian province/city dataset

`iran_provinces_cities_1404.json` is a compact application-owned derivative of
[`Hameds/IranCountryDivisions`](https://github.com/Hameds/IranCountryDivisions),
commit `68687cf96cc1852d5d38c7283353c80829331758`. The upstream project normalizes
the Statistical Centre of Iran's official annual geographic file for year 1404.
The repository preserves that original as
[`source/1404/geo_1404.xlsx`](https://github.com/Hameds/IranCountryDivisions/blob/main/source/1404/geo_1404.xlsx)
and documents its Statistical Centre addressing standard alongside it.
The source `data/1404/iran.json` SHA-256 is
`d493adef35d7b7187ce3c14b69794f0f6c66b4a9c9cdbfe9834cdb00e026e9e0`.

Only division type 1 (province) and division type 5 (actual city) rows are
included. Type 7 urban zones are intentionally excluded because they are
subdivisions of a city, not cities. Each city is associated with its province
by walking the official parent chain; its county name is retained to distinguish
same-name cities.

Completeness checks at generation and load time enforce 31 provinces and 1,481
cities. Official string codes are retained: two digits for provinces and four
globally unique digits for cities. There are 1,478 unique province/name pairs;
the official file contains three additional same-name city records:

- `گلوگاه` appears twice in Mazandaran (Babol and Galugah counties).
- `کشکوییه` appears twice in Kerman (Baft and Rafsanjan counties).
- `علی آباد` appears twice in Kerman (Jiroft and Arzuiyeh counties).

The derived data remains under the upstream MIT license; see
`LICENSE-IranCountryDivisions.txt`.
