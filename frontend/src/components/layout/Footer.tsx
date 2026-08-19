import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import type { StaticPageKey } from "@/lib/static-page-types";
import { getStaticPageVisibility } from "@/lib/static-pages";

type FooterLink = {
  label: string;
  href: string;
  pageKey?: StaticPageKey;
};

const columns: { title: string; links: FooterLink[] }[] = [
  {
    title: "گروه صنعتی توانا",
    links: [
      { label: "درباره ما", href: "/about", pageKey: "about" },
      { label: "تماس با ما", href: "/contact", pageKey: "contact" },
      // { label: "فرصت‌های شغلی", href: "#" },
      { label: "وبلاگ کشاورزی", href: "/blog" },
    ],
  },
  {
    title: "خدمات مشتریان",
    links: [
      { label: "پاسخ به پرسش‌ها", href: "/support", pageKey: "support" },
      { label: "رویه ارسال سفارش", href: "/help/shipping", pageKey: "shipping" },
      { label: "شرایط بازگشت کالا", href: "/help/returns", pageKey: "returns" },
      // "حریم خصوصی"
    ],
  },
  {
    title: "راهنمای خرید",
    links: [
      { label: "نحوه ثبت سفارش", href: "/help/how-to-order", pageKey: "how-to-order" },
      // "شیوه‌های پرداخت",
      { label: "رهگیری سفارش", href: "/help/track-order", pageKey: "track-order" },
      { label: "گارانتی محصولات", href: "/help/warranty", pageKey: "warranty" },
    ],
  },
];

function FooterColumns({
  visibility,
}: {
  visibility: Record<StaticPageKey, boolean> | null;
}) {
  return columns.map((col) => (
    <div key={col.title}>
      <h3 className="mb-3 font-bold text-slate-700">{col.title}</h3>
      <ul className="space-y-2 text-sm text-slate-500">
        {col.links
          .filter(
            (link) =>
              !link.pageKey || visibility?.[link.pageKey] === true
          )
          .map((link) => (
            <li key={link.label}>
              <Link
                href={link.href}
                className="transition hover:text-brand-700"
              >
                {link.label}
              </Link>
            </li>
          ))}
      </ul>
    </div>
  ));
}

async function ManagedFooterColumns() {
  const visibility = await getStaticPageVisibility();
  return <FooterColumns visibility={visibility} />;
}

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-10">
        {/* مزیت‌ها */}
        <div className="grid grid-cols-2 gap-4 border-b border-slate-100 pb-8 text-center sm:grid-cols-4">
          {[
            { icon: "🚚", text: "ارسال به سراسر کشور" },
            { icon: "✅", text: "ضمانت اصالت کالا" },
            { icon: "💳", text: "پرداخت امن و درب منزل" },
            { icon: "🎧", text: "پشتیبانی ۷ روز هفته" },
          ].map((f) => (
            <div key={f.text} className="flex flex-col items-center gap-2">
              <span className="text-3xl">{f.icon}</span>
              <span className="text-sm text-slate-600">{f.text}</span>
            </div>
          ))}
        </div>

        {/* ستون‌ها */}
        <div className="grid grid-cols-2 gap-8 py-8 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <div className="mb-3 flex items-center gap-2">
              <Image
                src="/brand/logo.png"
                alt=""
                width={40}
                height={40}
                className="h-10 w-10 object-contain"
              />
              <span className="text-lg font-bold text-brand-700">
                گروه صنعتی توانا
              </span>
            </div>
            <p className="text-sm leading-7 text-slate-500">
              فروشگاه اینترنتی ابزارآلات و ادوات کشاورزی؛ ارائه‌دهنده انواع ابزار
              باغبانی، سمپاش و ماشین‌آلات با بهترین قیمت و ضمانت اصالت کالا.
            </p>
          </div>
          <Suspense fallback={<FooterColumns visibility={null} />}>
            <ManagedFooterColumns />
          </Suspense>
        </div>

        <div className="border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
          © {new Date().getFullYear()} گروه صنعتی توانا — تمامی حقوق محفوظ است.
        </div>
      </div>
    </footer>
  );
}
