import { HomepageSections } from "@/components/homepage/HomepageSections";
import { getHomepageSections } from "@/lib/homepage";
import { fetchSeo, orgSchema, toMetadata } from "@/lib/seo";
import JsonLd from "@/components/seo/JsonLd";

// داده‌ها از دیتابیس خوانده می‌شوند؛ صفحه داینامیک است
export const dynamic = "force-dynamic";

// متاتگ‌های سئو از پنل سئو خوانده می‌شوند
export async function generateMetadata() {
  const seo = await fetchSeo("static", "/");
  return toMetadata(seo);
}

export default async function Home() {
  const [sections, seo] = await Promise.all([
    getHomepageSections(),
    fetchSeo("static", "/"),
  ]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {seo?.site.orgSchemaEnabled && <JsonLd data={orgSchema(seo.site)} />}
      <HomepageSections sections={sections} />
    </div>
  );
}
