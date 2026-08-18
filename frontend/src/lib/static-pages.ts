import "server-only";

import { cache } from "react";
import type {
  StaticPageContentMap,
  StaticPageKey,
} from "@/lib/static-page-types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

type PublicPageRecord = {
  key: StaticPageKey;
  content: unknown;
};

type PublicPagesResponse = {
  pages: PublicPageRecord[];
};

type PublicPageResponse = {
  page: PublicPageRecord;
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
): Promise<Pick<StaticPageContentMap, K> | null> {
  const uniqueKeys = [...new Set(keys)];
  const records = await fetchPageRecords(uniqueKeys.join(","));
  if (!records) return null;

  const result: Partial<StaticPageContentMap> = {};
  for (const key of uniqueKeys) {
    const record = records.find((item) => item.key === key);
    if (!record || !record.content || typeof record.content !== "object") {
      return null;
    }
    result[key] = record.content as never;
  }

  return result as Pick<StaticPageContentMap, K>;
}

export async function getStaticPage<K extends StaticPageKey>(
  key: K
): Promise<StaticPageContentMap[K] | null> {
  const page = await fetchPageRecord(key);
  if (page?.key !== key || !page.content || typeof page.content !== "object") {
    return null;
  }
  return page.content as StaticPageContentMap[K];
}
