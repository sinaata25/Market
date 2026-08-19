import "server-only";

import { cache } from "react";
import type {
  StaticPageKey,
  StaticPageRecordMap,
} from "@/lib/static-page-types";
import { STATIC_PAGE_KEYS } from "@/lib/static-page-types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

type PublicPageRecord = {
  key: StaticPageKey;
  isVisible: boolean;
  sections: unknown;
  content: unknown;
};

type PublicPagesResponse = {
  pages: PublicPageRecord[];
};

type PublicPageResponse = {
  page: PublicPageRecord;
};

type PublicPageVisibilityResponse = {
  pages: { key: StaticPageKey; isVisible: boolean }[];
};

const fetchPageRecord = cache(
  async (key: StaticPageKey): Promise<PublicPageRecord | null> => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/content/pages/${encodeURIComponent(key)}`,
        { cache: "no-store" }
      );
      const json = await response.json().catch(() => null);
      if (!response.ok || !json?.ok || !json.data?.page) return null;
      return (json.data as PublicPageResponse).page;
    } catch {
      return null;
    }
  }
);

const fetchPageRecords = cache(
  async (keyList: string): Promise<PublicPageRecord[] | null> => {
    try {
      const query = new URLSearchParams({ keys: keyList });
      const response = await fetch(
        `${BACKEND_URL}/api/content/pages?${query.toString()}`,
        { cache: "no-store" }
      );
      const json = await response.json().catch(() => null);
      if (!response.ok || !json?.ok || !Array.isArray(json.data?.pages)) {
        return null;
      }
      return (json.data as PublicPagesResponse).pages;
    } catch {
      return null;
    }
  }
);

export async function getStaticPages<K extends StaticPageKey>(
  keys: readonly K[]
): Promise<Pick<StaticPageRecordMap, K> | null> {
  const uniqueKeys = [...new Set(keys)];
  const records = await fetchPageRecords(uniqueKeys.join(","));
  if (!records) return null;

  const result: Partial<StaticPageRecordMap> = {};
  for (const key of uniqueKeys) {
    const record = records.find((item) => item.key === key);
    if (
      !record ||
      typeof record.isVisible !== "boolean" ||
      !record.sections ||
      typeof record.sections !== "object" ||
      !record.content ||
      typeof record.content !== "object"
    ) {
      return null;
    }
    result[key] = record as never;
  }

  return result as Pick<StaticPageRecordMap, K>;
}

export async function getStaticPage<K extends StaticPageKey>(
  key: K
): Promise<StaticPageRecordMap[K] | null> {
  const page = await fetchPageRecord(key);
  if (
    page?.key !== key ||
    typeof page.isVisible !== "boolean" ||
    !page.sections ||
    typeof page.sections !== "object" ||
    !page.content ||
    typeof page.content !== "object"
  ) {
    return null;
  }
  return page as StaticPageRecordMap[K];
}

export async function getStaticPageVisibility(): Promise<
  Record<StaticPageKey, boolean> | null
> {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/content/pages/visibility`,
      { cache: "no-store" }
    );
    const json = await response.json().catch(() => null);
    if (!response.ok || !json?.ok || !Array.isArray(json.data?.pages)) {
      return null;
    }

    const pages = (json.data as PublicPageVisibilityResponse).pages;
    const result = Object.fromEntries(
      pages.map((page) => [page.key, page.isVisible])
    ) as Partial<Record<StaticPageKey, boolean>>;
    if (
      pages.length !== STATIC_PAGE_KEYS.length ||
      pages.some(
        (page) =>
          !STATIC_PAGE_KEYS.includes(page.key) ||
          typeof page.isVisible !== "boolean"
      ) ||
      STATIC_PAGE_KEYS.some((key) => typeof result[key] !== "boolean")
    ) {
      return null;
    }
    return result as Record<StaticPageKey, boolean>;
  } catch {
    return null;
  }
}
