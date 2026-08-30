import Link from "next/link";
import FooterShopLocation from "@/components/layout/FooterShopLocation";
import { getFooter } from "@/lib/footer";
import { shopLocationToRender } from "@/lib/footer-map";
import type { FooterItem, FooterSection, FooterSettings } from "@/lib/footer";
import {
  footerColumnGridClass,
  footerLinkAttributes,
  partitionFooterSections,
} from "@/lib/footer-layout";

// تنها دارایی ثابت فوتر: لوگوی پیش‌فرض فروشگاه، وقتی مدیر لوگویی آپلود
// نکرده باشد. بقیه‌ی محتوا کاملاً از API می‌آید.
const FALLBACK_LOGO = "/brand/logo.png";

const LINK_CLASS = "transition hover:text-brand-700";

function ItemLink({
  item,
  className,
  children,
}: {
  item: FooterItem;
  className: string;
  children: React.ReactNode;
}) {
  const attributes = footerLinkAttributes(item);
  // محتوای بی‌مقصد (متن، نشانی، تصویر بدون لینک) نباید حالت hover پیوند بگیرد
  if (!attributes) return <span>{children}</span>;

  const { href, external, ...rest } = attributes;
  if (external) {
    return (
      <a href={href} className={className} {...rest}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className} {...rest}>
      {children}
    </Link>
  );
}

/** محتوای درونی یک آیتم — آیکن اختیاری به‌علاوه‌ی متن یا تصویرش */
function ItemBody({ item }: { item: FooterItem }) {
  if (item.type === "image" && item.image) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={item.image}
        alt={item.label ?? ""}
        loading="lazy"
        className="h-10 w-auto max-w-full object-contain"
      />
    );
  }

  const value =
    item.type === "link" || item.type === "social"
      ? item.label
      : (item.text ?? item.label);

  // پیوند ساده‌ی بی‌آیکن دقیقاً همان متن قبلی فوتر است — بدون قاب اضافه
  if (!item.icon && item.type !== "phone" && item.type !== "email") {
    return <>{value}</>;
  }

  // شماره و ایمیل باید چپ‌به‌راست خوانده شوند، حتی داخل صفحه‌ی راست‌به‌چپ
  const ltr = item.type === "phone" || item.type === "email";
  return (
    <span className="inline-flex items-start gap-1.5">
      {item.icon && <span aria-hidden="true">{item.icon}</span>}
      <span
        dir={ltr ? "ltr" : undefined}
        className={ltr ? "min-w-0 font-num" : "min-w-0 whitespace-pre-line"}
      >
        {value}
      </span>
    </span>
  );
}

function ColumnSection({ section }: { section: FooterSection }) {
  return (
    <div className="min-w-0">
      {section.title && (
        <h3 className="mb-3 font-bold text-slate-700">{section.title}</h3>
      )}
      {section.description && (
        <p className="mb-3 text-sm leading-7 text-slate-500">
          {section.description}
        </p>
      )}
      <ul className="space-y-2 text-sm text-slate-500">
        {section.items.map((item) => (
          <li key={item.id} className="min-w-0">
            <ItemLink item={item} className={LINK_CLASS}>
              <ItemBody item={item} />
            </ItemLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StripSection({ section }: { section: FooterSection }) {
  return (
    <div className="grid grid-cols-2 gap-4 border-b border-slate-100 pb-8 text-center sm:grid-cols-[repeat(auto-fit,minmax(9rem,1fr))]">
      {section.items.map((item) => (
        <div key={item.id} className="flex min-w-0 flex-col items-center gap-2">
          {item.icon && <span className="text-3xl">{item.icon}</span>}
          <span className="text-sm text-slate-600">
            <ItemLink item={item} className={LINK_CLASS}>
              {item.text ?? item.label}
            </ItemLink>
          </span>
        </div>
      ))}
    </div>
  );
}

function BrandColumn({ settings }: { settings: FooterSettings }) {
  const contactRows = [
    settings.address && { key: "address", icon: "📍", text: settings.address, href: null },
    settings.phone && {
      key: "phone",
      icon: "☎️",
      text: settings.phone,
      href: settings.phoneUrl,
    },
    settings.email && {
      key: "email",
      icon: "✉️",
      text: settings.email,
      href: settings.emailUrl,
    },
  ].filter(Boolean) as {
    key: string;
    icon: string;
    text: string;
    href: string | null;
  }[];

  return (
    <div className="col-span-2 min-w-0 md:col-span-1">
      <div className="mb-3 flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={settings.logo ?? FALLBACK_LOGO}
          alt=""
          width={40}
          height={40}
          className="h-10 w-10 object-contain"
        />
        {settings.brandTitle && (
          <span className="text-lg font-bold text-brand-700">
            {settings.brandTitle}
          </span>
        )}
      </div>
      {settings.description && (
        <p className="text-sm leading-7 text-slate-500 whitespace-pre-line">
          {settings.description}
        </p>
      )}
      {contactRows.length > 0 && (
        <ul className="mt-4 space-y-2 text-sm text-slate-500">
          {contactRows.map((row) => (
            <li key={row.key} className="flex items-start gap-1.5">
              <span aria-hidden="true">{row.icon}</span>
              {row.href ? (
                <a
                  href={row.href}
                  dir="ltr"
                  className={`min-w-0 font-num ${LINK_CLASS}`}
                >
                  {row.text}
                </a>
              ) : (
                <span className="min-w-0">{row.text}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default async function Footer() {
  const footer = await getFooter();

  // بک‌اند در دسترس نیست: به‌جای شکستن صفحه، فقط قاب فوتر رندر می‌شود
  if (!footer) {
    return <footer className="mt-12 border-t border-slate-200 bg-white" />;
  }

  const { settings, sections } = footer;
  const { strips, columns } = partitionFooterSections(sections);
  const location = shopLocationToRender(settings.location);

  return (
    <footer className="mt-12 border-t border-slate-200 bg-white">
      <div className="site-shell py-10">
        {strips.map((section) => (
          <StripSection key={section.id} section={section} />
        ))}

        <div
          className={`grid grid-cols-2 gap-8 py-8 ${footerColumnGridClass(columns.length)}`}
        >
          <BrandColumn settings={settings} />
          {columns.map((section) => (
            <ColumnSection key={section.id} section={section} />
          ))}
        </div>

        {location && <FooterShopLocation location={location} />}

        {settings.copyright && (
          <div className="border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
            {settings.copyright}
          </div>
        )}
      </div>
    </footer>
  );
}
