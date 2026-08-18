import SupportContent from "@/components/static-pages/SupportContent";
import StaticPageUnavailable from "@/components/static-pages/StaticPageUnavailable";
import { getStaticPages } from "@/lib/static-pages";

export const dynamic = "force-dynamic";

export default async function SupportPage() {
  const pages = await getStaticPages(["support", "contact"]);
  if (!pages) return <StaticPageUnavailable />;

  return (
    <SupportContent
      content={pages.support}
      contactPhone={pages.contact.ways[0].phoneNumber}
    />
  );
}
