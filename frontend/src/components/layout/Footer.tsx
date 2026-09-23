import Link from "next/link";
import FooterIcon from "@/components/layout/FooterIcon";
import FooterShopLocation from "@/components/layout/FooterShopLocation";
import FooterTrustBadges from "@/components/layout/FooterTrustBadges";
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
  if (!attributes) return <span className={className}>{children}</span>;

  const { href, external, ...rest } = attributes;
  const linkedClassName = `${className} ${LINK_CLASS}`;
  if (external) {
    return (
      <a href={href} className={linkedClassName} {...rest}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={linkedClassName} {...rest}>
      {children}
    </Link>
  );
}

function itemValue(item: FooterItem, hasVisual: boolean): string | null {
  const value =
    item.type === "link" || item.type === "social"
      ? item.label
      : (item.text ?? item.label);

  // شبکه‌ی اجتماعی می‌تواند طبق قرارداد بک‌اند فقط URL داشته باشد. اگر آیکنی
  // هم ندارد، خود مقصد را نشان می‌دهیم تا یک پیوند نامرئی ساخته نشود.
  return value ?? (!hasVisual ? item.url : null);
}

function itemIsLtr(item: FooterItem): boolean {
  return item.type === "phone" || item.type === "email";
}

function itemHasVisual(item: FooterItem): boolean {
  return Boolean(
    (item.type === "image" && item.image) || item.iconImage || item.icon
  );
}

/** محتوای درونی یک آیتم — برای ستون افقی و برای نوار مزیت عمودی است. */
function ItemBody({
  item,
  variant = "column",
  reserveVisualSpace = false,
}: {
  item: FooterItem;
  variant?: "column" | "strip";
  reserveVisualSpace?: boolean;
}) {
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

  const hasIcon = Boolean(item.iconImage || item.icon);
  const value = itemValue(item, hasIcon);
  const ltr = itemIsLtr(item);
  const text = value && (
    <bdi
      dir={ltr ? "ltr" : "auto"}
      className={`min-w-0 whitespace-pre-line leading-6 [overflow-wrap:anywhere] ${
        ltr ? "font-num" : ""
      }`}
    >
      {value}
    </bdi>
  );

  if (variant === "strip") {
    return (
      <span className="flex min-w-0 flex-col items-center gap-2 text-center">
        {(hasIcon || reserveVisualSpace) && (
          <span
            className="flex size-10 items-center justify-center"
            aria-hidden={!hasIcon}
          >
            <FooterIcon
              image={item.iconImage}
              emoji={item.icon}
              className="size-10 text-3xl"
            />
          </span>
        )}
        {text}
      </span>
    );
  }

  // پیوند ساده‌ی بی‌آیکن همان متن فوتر می‌ماند و جای خالی آیکن نمی‌گیرد.
  if (!hasIcon) return text;

  return (
    <span className="flex min-w-0 items-start gap-2">
      <FooterIcon
        image={item.iconImage}
        emoji={item.icon}
        className="size-6 p-0.5 text-base"
      />
      {text}
    </span>
  );
}

function ColumnSection({ section }: { section: FooterSection }) {
  return (
    <section className="min-w-0">
      {section.title && (
        <h3 className="mb-3 font-bold leading-6 text-slate-700">
          {section.title}
        </h3>
      )}
      {section.description && (
        <p className="mb-3 whitespace-pre-line text-sm leading-7 text-slate-500">
          {section.description}
        </p>
      )}
      <ul className="space-y-2 text-sm leading-6 text-slate-500">
        {section.items.map((item) => (
          <li key={item.id} className="min-w-0">
            <ItemLink item={item} className="inline-block max-w-full align-top">
              <ItemBody item={item} />
            </ItemLink>
          </li>
        ))}
      </ul>
    </section>
  );
}

function StripSection({ section }: { section: FooterSection }) {
  const reserveVisualSpace = section.items.some(itemHasVisual);

  return (
    <section className="border-b border-slate-100 py-8 first:pt-0">
      {(section.title || section.description) && (
        <header className="mb-5 min-w-0">
          {section.title && (
            <h3 className="font-bold leading-6 text-slate-700">{section.title}</h3>
          )}
          {section.description && (
            <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-500">
              {section.description}
            </p>
          )}
        </header>
      )}
      <ul className="grid grid-cols-[repeat(auto-fit,minmax(min(8rem,100%),1fr))] gap-4 text-sm text-slate-600 sm:grid-cols-[repeat(auto-fit,minmax(min(9rem,100%),1fr))]">
        {section.items.map((item) => (
          <li key={item.id} className="min-w-0">
            <ItemLink
              item={item}
              className="flex h-full min-w-0 items-start justify-center"
            >
              <ItemBody
                item={item}
                variant="strip"
                reserveVisualSpace={reserveVisualSpace}
              />
            </ItemLink>
          </li>
        ))}
      </ul>
    </section>
  );
}

function BrandColumn({ settings }: { settings: FooterSettings }) {
  const contactRows = [
    settings.address && {
      key: "address",
      icon: settings.addressIcon,
      text: settings.address,
      href: null,
    },
    settings.phone && {
      key: "phone",
      icon: settings.phoneIcon,
      text: settings.phone,
      href: settings.phoneUrl,
    },
    settings.email && {
      key: "email",
      icon: settings.emailIcon,
      text: settings.email,
      href: settings.emailUrl,
    },
  ].filter(Boolean) as {
    key: string;
    icon: string | null;
    text: string;
    href: string | null;
  }[];

  return (
    <section className="col-span-full min-w-0 lg:col-span-1">
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
          <span className="min-w-0 text-lg font-bold leading-7 text-brand-700 [overflow-wrap:anywhere]">
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
        <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-500">
          {contactRows.map((row) => (
            <li key={row.key} className="flex min-w-0 items-start gap-2">
              <FooterIcon image={row.icon} className="size-6 p-0.5 text-base" />
              {row.href ? (
                <a href={row.href} className={`min-w-0 ${LINK_CLASS}`}>
                  <bdi
                    dir="ltr"
                    className="font-num whitespace-pre-line [overflow-wrap:anywhere]"
                  >
                    {row.text}
                  </bdi>
                </a>
              ) : (
                <bdi
                  dir="auto"
                  className="min-w-0 whitespace-pre-line [overflow-wrap:anywhere]"
                >
                  {row.text}
                </bdi>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default async function Footer() {
  const footer = await getFooter();

  // بک‌اند در دسترس نیست: به‌جای شکستن صفحه، فقط قاب فوتر رندر می‌شود
  if (!footer) {
    return <footer className="mt-12 border-t border-slate-200 bg-white" />;
  }

  const { settings, sections } = footer;
  const { strips, columns, badges } = partitionFooterSections(sections);
  const location = shopLocationToRender(settings.location);

  return (
    <footer className="mt-12 border-t border-slate-200 bg-white">
      <div className="site-shell py-10">
        {strips.map((section) => (
          <StripSection key={section.id} section={section} />
        ))}

        <div
          className={`grid grid-cols-[repeat(auto-fit,minmax(min(10rem,100%),1fr))] gap-x-8 gap-y-10 py-8 sm:grid-cols-2 ${footerColumnGridClass(columns.length)}`}
        >
          <BrandColumn settings={settings} />
          {columns.map((section) => (
            <ColumnSection key={section.id} section={section} />
          ))}
        </div>

        {location && <FooterShopLocation location={location} />}

        {badges.map((section) => <FooterTrustBadges key={section.id} section={section} />)}

        {settings.copyright && (
          <div className="border-t border-slate-100 pt-6 text-center text-xs text-slate-400 whitespace-pre-line [overflow-wrap:anywhere]">
            {settings.copyright}
          </div>
        )}
      </div>
    </footer>
  );
}
