"use client";

import { api, type ApiResult } from "@/lib/client-api";
import { createLocationsApi } from "@/lib/location-options";

export * from "@/lib/location-options";

export const locationsApi = createLocationsApi(
  <T>(path: string): Promise<ApiResult<T>> => api.get<T>(path)
);
