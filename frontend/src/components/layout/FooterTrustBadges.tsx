import { badgeLinkAttributes, visibleTrustBadges, type FooterTrustBadge } from "@/lib/footer-trust-badges";

export default function FooterTrustBadges({ section }: {
  section: { id: number; title: string | null; items: FooterTrustBadge[]; isActive?: boolean };
}) {
  const badges = visibleTrustBadges(section.items);
  if (section.isActive === false || badges.length === 0) return null;

  return (
    <section aria-labelledby={`footer-trust-title-${section.id}`} className="border-t border-slate-100 py-6">
      <h3 id={`footer-trust-title-${section.id}`} className="mb-4 text-center font-bold text-slate-700 sm:text-start">
        {section.title || "نمادها و مجوزها"}
      </h3>
      <ul className="flex flex-wrap justify-center gap-3 sm:justify-start sm:gap-4">
        {badges.map((badge) => (
          <li key={badge.id} className="w-24 max-w-full sm:w-28">
            <a {...badgeLinkAttributes(badge)} className="flex h-28 items-center justify-center rounded-2xl border border-slate-200 bg-white p-3 shadow-sm transition-colors hover:border-brand-500 hover:bg-brand-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 sm:h-32">
              {/* Validated local uploads; SVG is rendered as an image, never inline HTML. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={badge.image!} alt={badge.altText?.trim() || badge.label!} width={96} height={96} loading="lazy" decoding="async" className="h-full w-full max-w-full object-contain" />
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
