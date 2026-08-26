export type ProvinceOption = {
  id: string;
  name: string;
};

export type CityOption = ProvinceOption & {
  countyName: string;
};

export type ProvinceCityValue = {
  province: string;
  city: string;
  provinceId: string | null;
  cityId: string | null;
};

export type ProvincesResponse = {
  provinces: ProvinceOption[];
};

export type CitiesResponse = {
  province: ProvinceOption;
  cities: CityOption[];
};

type LocationApiResult<T> = {
  ok: boolean;
  data?: T;
  error?: string;
  status: number;
};

type LocationGet = <T>(path: string) => Promise<LocationApiResult<T>>;

type RequestOptions = {
  force?: boolean;
};

export const PROVINCES_API_PATH = "/api/locations/provinces";

export function provinceCitiesApiPath(provinceId: string): string {
  return `${PROVINCES_API_PATH}/${encodeURIComponent(provinceId)}/cities`;
}

export function normalizeLocationName(name: string): string {
  return name
    .normalize("NFKC")
    .replace(/[يى]/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/[أإ]/g, "ا")
    .replace(/[ةۀ]/g, "ه")
    .replace(/ـ/g, "")
    .replace(/\p{Mn}/gu, "")
    .trim()
    .replace(/\s+/gu, " ");
}

export function resolveLocationOption<T extends ProvinceOption>(
  options: T[],
  id: string | null | undefined,
  name: string
): T | null {
  if (id) return options.find((option) => option.id === id) ?? null;

  const normalizedName = normalizeLocationName(name);
  const optionsWithName = options.filter(
    (option) => normalizeLocationName(option.name) === normalizedName
  );
  return optionsWithName.length === 1 ? optionsWithName[0] : null;
}

export function cityOptionLabel(
  city: CityOption,
  cities: CityOption[]
): string {
  const duplicateName = cities.some(
    (candidate) => candidate.id !== city.id && candidate.name === city.name
  );
  return duplicateName && city.countyName
    ? `${city.name} — شهرستان ${city.countyName}`
    : city.name;
}

export function locationAfterProvinceChange(
  provinces: ProvinceOption[],
  provinceId: string
): ProvinceCityValue {
  const selectedProvince =
    provinces.find((province) => province.id === provinceId) ?? null;
  return {
    province: selectedProvince?.name ?? "",
    city: "",
    provinceId: selectedProvince?.id ?? null,
    cityId: null,
  };
}

export function createLocationsApi(get: LocationGet) {
  let provincesRequest: Promise<LocationApiResult<ProvincesResponse>> | null =
    null;
  const cityRequests = new Map<
    string,
    Promise<LocationApiResult<CitiesResponse>>
  >();

  function getProvinces(
    options: RequestOptions = {}
  ): Promise<LocationApiResult<ProvincesResponse>> {
    if (options.force) provincesRequest = null;
    if (provincesRequest) return provincesRequest;

    const request: Promise<LocationApiResult<ProvincesResponse>> =
      get<ProvincesResponse>(PROVINCES_API_PATH).then(
        (result) => {
          if (!result.ok && provincesRequest === request) {
            provincesRequest = null;
          }
          return result;
        },
        (error: unknown) => {
          if (provincesRequest === request) provincesRequest = null;
          throw error;
        }
      );
    provincesRequest = request;
    return request;
  }

  function getCities(
    provinceId: string,
    options: RequestOptions = {}
  ): Promise<LocationApiResult<CitiesResponse>> {
    if (options.force) cityRequests.delete(provinceId);
    const cached = cityRequests.get(provinceId);
    if (cached) return cached;

    const request: Promise<LocationApiResult<CitiesResponse>> =
      get<CitiesResponse>(provinceCitiesApiPath(provinceId)).then(
        (result) => {
          if (!result.ok && cityRequests.get(provinceId) === request) {
            cityRequests.delete(provinceId);
          }
          return result;
        },
        (error: unknown) => {
          if (cityRequests.get(provinceId) === request) {
            cityRequests.delete(provinceId);
          }
          throw error;
        }
      );
    cityRequests.set(provinceId, request);
    return request;
  }

  return { getProvinces, getCities };
}
