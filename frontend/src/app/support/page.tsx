import SupportContent from "@/components/static-pages/SupportContent";
import StaticPageUnavailable from "@/components/static-pages/StaticPageUnavailable";
import { getStaticPages } from "@/lib/static-pages";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function SupportPage() {
  const pages = await getStaticPages(["support", "contact"]);
  if (!pages) return <StaticPageUnavailable />;
  if (!pages.support.isVisible) notFound();

  return (
    <SupportContent
      content={pages.support.content}
      sections={pages.support.sections}
      contactPhone={pages.contact.content.ways[0].phoneNumber}
    />
  );
}
