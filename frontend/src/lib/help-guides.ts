import type { HelpPageKey } from "@/lib/static-page-types";

type HelpGuideRoute = {
  key: HelpPageKey;
  slug: string;
  icon: string;
  stepHrefs: readonly (string | null)[];
  ctaHref: string;
};

export const helpGuideRoutes = [
  {
    key: "how-to-order",
    slug: "how-to-order",
    icon: "🛒",
    stepHrefs: ["/", "/cart", null, "/login", null],
    ctaHref: "/",
  },
  {
    key: "track-order",
    slug: "track-order",
    icon: "📦",
    stepHrefs: ["/login", "/profile/orders", null],
    ctaHref: "/profile/orders",
  },
  {
    key: "warranty",
    slug: "warranty",
    icon: "🛡️",
    stepHrefs: [null, null, "/contact"],
    ctaHref: "/contact",
  },
  {
    key: "shipping",
    slug: "shipping",
    icon: "🚚",
    stepHrefs: [null, null, null, "/help/track-order"],
    ctaHref: "/profile/orders",
  },
  {
    key: "returns",
    slug: "returns",
    icon: "↩️",
    stepHrefs: [null, "/profile/orders", "/contact", null],
    ctaHref: "/contact",
  },
] as const satisfies readonly HelpGuideRoute[];

export const helpPageKeys = helpGuideRoutes.map((guide) => guide.key);

export function getHelpGuideRoute(slug: string) {
  return helpGuideRoutes.find((guide) => guide.slug === slug);
}
