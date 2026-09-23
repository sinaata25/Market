/** Public footer items are already filtered by the API. Optional status also
 * permits rendering an admin preview without showing disabled items. */
export type FooterTrustBadge = {
  id: number;
  type: string;
  label: string | null;
  image: string | null;
  url: string | null;
  altText?: string | null;
  openInNewTab: boolean;
  position: number;
  isActive?: boolean;
};

export function badgeLinkAttributes(badge: FooterTrustBadge) {
  if (!badge.url || !/^https?:\/\//i.test(badge.url) || /[\\<>\s]/.test(badge.url)) return null;
  try {
    const url = new URL(badge.url);
    if (url.username || url.password || !url.hostname) return null;
  } catch {
    return null;
  }
  return {
    href: badge.url,
    target: badge.openInNewTab ? "_blank" : undefined,
    rel: badge.openInNewTab ? "noopener noreferrer" : undefined,
  };
}

export function visibleTrustBadges(items: readonly FooterTrustBadge[]) {
  return items
    .filter((item) => item.type === "badge" && item.isActive !== false && item.image?.trim() && item.label?.trim() && badgeLinkAttributes(item))
    .sort((a, b) => a.position - b.position || a.id - b.id);
}
