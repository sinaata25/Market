import "server-only";
import type { Metadata } from "next";

// دریافت متای سئو از بک‌اند و تبدیل به Metadata نکست
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export type SeoPayload = {
  meta: {
    effectiveTitle: string;
    effectiveDescription: string;
    effectiveImage: string;
    canonical: string;
    robotsIndex: boolean;
    robotsFollow: boolean;
    ogTitle: string;
    ogDescription: string;
    twitterCard: string;
    slug: string;
    path: string | null;
  };
  schema: Record<string, unknown> | null;
  site: {
    name: string;
    url: string;
    breadcrumbsEnabled: boolean;
    lazyloadEnabled: boolean;
    orgSchemaEnabled: boolean;
    hreflang: { lang: string; url: string }[];
  };
};

export async function fetchSeo(
  type: "product" | "category" | "static",
  key: string
): Promise<SeoPayload | null> {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/seo/meta?type=${type}&key=${encodeURIComponent(key)}`,
      { cache: "no-store" }
    );
    const json = await res.json();
    return json.ok ? (json.data as SeoPayload) : null;
  } catch {
    return null;
  }
}

// تبدیل به آبجکت Metadata نکست
export function toMetadata(seo: SeoPayload | null): Metadata {
  if (!seo) return {};
  const { meta, site } = seo;

  const canonical =
    meta.canonical ||
    (meta.slug && meta.path?.startsWith("/product/")
      ? `${site.url}/product/${meta.slug}`
      : meta.path
        ? `${site.url}${meta.path}`
        : undefined);

  const languages: Record<string, string> = {};
  for (const h of site.hreflang) languages[h.lang] = h.url;

  return {
    title: meta.effectiveTitle,
    description: meta.effectiveDescription,
    robots: {
      index: meta.robotsIndex,
      follow: meta.robotsFollow,
    },
    alternates: {
      canonical,
      ...(Object.keys(languages).length > 0 ? { languages } : {}),
    },
    openGraph: {
      title: meta.ogTitle || meta.effectiveTitle,
      description: meta.ogDescription || meta.effectiveDescription,
      siteName: site.name,
      ...(meta.effectiveImage
        ? { images: [`${site.url}${meta.effectiveImage}`] }
        : {}),
      type: "website",
      locale: "fa_IR",
    },
    twitter: {
      card: meta.twitterCard === "summary" ? "summary" : "summary_large_image",
      title: meta.ogTitle || meta.effectiveTitle,
      description: meta.ogDescription || meta.effectiveDescription,
    },
  };
}

// اسکیمای بردکرامب
export function breadcrumbSchema(
  site: SeoPayload["site"],
  items: { name: string; path: string }[]
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: `${site.url}${item.path}`,
    })),
  };
}

// اسکیمای Organization برای صفحه اصلی
export function orgSchema(site: SeoPayload["site"]) {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: site.name,
    url: site.url,
  };
}
