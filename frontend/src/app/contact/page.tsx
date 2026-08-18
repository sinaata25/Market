import type { Metadata } from "next";
import Link from "next/link";
import StaticPageUnavailable from "@/components/static-pages/StaticPageUnavailable";
import { getStaticPage } from "@/lib/static-pages";

export const metadata: Metadata = {
  title: "تماس با ما | گروه صنعتی توانا",
  description:
    "راه‌های ارتباط با گروه صنعتی توانا برای مشاوره خرید، پیگیری سفارش و دریافت پشتیبانی.",
};

export const dynamic = "force-dynamic";

const contactWayRoutes = [
  { icon: "phone", href: null, external: true },
  { icon: "order", href: "/profile/orders", external: false },
  { icon: "help", href: "/support", external: false },
] as const;
const topicNumbers = ["۰۱", "۰۲", "۰۳"] as const;

function ContactIcon({ name }: { name: (typeof contactWayRoutes)[number]["icon"] }) {
  if (name === "phone") {
    return (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-7 w-7">
        <path d="M8.1 4.5 9.7 8a1.5 1.5 0 0 1-.4 1.8l-1.2.9a13.2 13.2 0 0 0 5.2 5.2l.9-1.2a1.5 1.5 0 0 1 1.8-.4l3.5 1.6a1.5 1.5 0 0 1 .8 1.7l-.4 1.8a2 2 0 0 1-2 1.6A15 15 0 0 1 3 6.1a2 2 0 0 1 1.6-2l1.8-.4a1.5 1.5 0 0 1 1.7.8Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (name === "order") {
    return (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-7 w-7">
        <path d="M5 8.5h14v11H5v-11Zm2.5 0V7a4.5 4.5 0 0 1 9 0v1.5M9 13h6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-7 w-7">
      <path d="M20 11.5a7.5 7.5 0 0 1-8 7.5 9.4 9.4 0 0 1-3.4-.7L4 20l1.5-4A7.4 7.4 0 0 1 4 11.5 7.5 7.5 0 0 1 12 4a7.5 7.5 0 0 1 8 7.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M10.2 9.5A2 2 0 1 1 13 11.3c-.7.4-1 .8-1 1.7M12 16h.01" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export default async function ContactPage() {
  const content = await getStaticPage("contact");
  if (!content) return <StaticPageUnavailable />;

  return (
    <div className="overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:pt-8">
        <nav aria-label="مسیر راهنما" className="mb-5 flex items-center gap-2 text-xs text-slate-500">
          <Link href="/" className="transition hover:text-brand-700">
            خانه
          </Link>
          <span className="text-slate-300">/</span>
          <span className="font-medium text-brand-700">تماس با ما</span>
        </nav>

        <section className="relative isolate overflow-hidden rounded-[2rem] bg-gradient-to-l from-brand-800 via-brand-700 to-secondary-800 px-6 py-12 text-white shadow-[0_24px_80px_-45px_rgba(20,36,79,0.8)] sm:px-10 sm:py-16 lg:px-16 lg:py-20">
          <div className="absolute inset-0 -z-20 bg-[radial-gradient(circle_at_15%_15%,rgba(228,176,40,0.25),transparent_27%),radial-gradient(circle_at_85%_100%,rgba(255,255,255,0.12),transparent_32%)]" />
          <div className="absolute -left-20 -top-24 -z-10 h-80 w-80 rounded-full border-[55px] border-white/5" />

          <div className="grid items-end gap-10 lg:grid-cols-[1fr_auto]">
            <div className="max-w-2xl">
              <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs text-brand-50 backdrop-blur-sm">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-300 opacity-60" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent-400" />
                </span>
                {content.hero.badge}
              </span>
              <h1 className="text-3xl font-bold leading-[1.55] sm:text-4xl lg:text-5xl">
                {content.hero.title}
                {" "}
                <span className="text-accent-300">{content.hero.accent}</span>
                {" "}
                {content.hero.suffix}
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-8 text-brand-50/90 sm:text-base sm:leading-9">
                {content.hero.intro}
              </p>
            </div>

            <div className="hidden h-40 w-52 shrink-0 items-end justify-center lg:flex" aria-hidden="true">
              <div className="relative h-28 w-40 rounded-t-[5rem] border-2 border-white/20 border-b-0">
                <span className="absolute -right-5 bottom-0 h-16 w-10 rounded-r-2xl border-2 border-white/30 bg-white/10" />
                <span className="absolute -left-5 bottom-0 h-16 w-10 rounded-l-2xl border-2 border-white/30 bg-white/10" />
                <span className="absolute bottom-4 left-1/2 h-2 w-16 -translate-x-1/2 rounded-full bg-accent-300" />
              </div>
            </div>
          </div>
        </section>

        <section className="relative z-10 -mt-6 grid gap-4 px-3 md:grid-cols-3 sm:px-6 lg:px-10">
          {content.ways.map((way, index) => {
            const route = contactWayRoutes[index];
            const href = route.href ?? `tel:${content.ways[0].phoneNumber}`;
            const className =
              "group flex min-h-72 flex-col rounded-3xl border border-slate-100 bg-white p-6 shadow-[0_18px_50px_-35px_rgba(20,36,79,0.55)] transition hover:-translate-y-1 hover:border-brand-200 sm:p-7";
            const cardContent = (
              <>
                <div className="mb-8 flex items-start justify-between">
                  <span className="grid h-13 w-13 place-items-center rounded-2xl bg-brand-50 text-brand-700 transition group-hover:bg-brand-600 group-hover:text-white">
                    <ContactIcon name={route.icon} />
                  </span>
                  <span className="text-[11px] font-medium text-slate-400">{way.eyebrow}</span>
                </div>
                <h2 className="text-lg font-bold text-secondary-900">{way.title}</h2>
                <p className="mt-3 flex-1 text-sm leading-7 text-slate-500">{way.description}</p>
                <span className="mt-6 flex items-center justify-between border-t border-slate-100 pt-5 text-sm font-bold text-brand-700">
                  <span dir={route.external ? "ltr" : "rtl"}>{way.label}</span>
                  <span className="text-lg transition group-hover:-translate-x-1">←</span>
                </span>
              </>
            );

            return route.external ? (
              <a key={index} href={href} className={className}>
                {cardContent}
              </a>
            ) : (
              <Link key={index} href={href} className={className}>
                {cardContent}
              </Link>
            );
          })}
        </section>

        <section className="grid gap-10 py-16 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20 lg:py-24">
          <div>
            <p className="mb-3 text-sm font-bold text-brand-600">{content.topics.eyebrow}</p>
            <h2 className="text-2xl font-bold leading-10 text-secondary-900 sm:text-3xl">
              {content.topics.title}
            </h2>
            <p className="mt-4 max-w-md text-sm leading-8 text-slate-500">
              {content.topics.description}
            </p>
          </div>
          <ol className="divide-y divide-slate-100 overflow-hidden rounded-3xl border border-slate-100 bg-white">
            {content.topics.items.map((topic, index) => (
              <li key={topicNumbers[index]} className="grid gap-3 p-6 sm:grid-cols-[3.5rem_1fr] sm:gap-5 sm:p-7">
                <span className="font-num text-xl font-bold text-accent-600">{topicNumbers[index]}</span>
                <div>
                  <h3 className="font-bold text-secondary-900">{topic.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-500">{topic.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="grid overflow-hidden rounded-[2rem] bg-white shadow-[0_20px_70px_-50px_rgba(31,61,137,0.7)] lg:grid-cols-[1fr_0.95fr]">
          <div className="p-7 sm:p-10 lg:p-12">
            <span className="mb-5 grid h-12 w-12 place-items-center rounded-2xl bg-accent-50 text-2xl">🌱</span>
            <p className="mb-2 text-sm font-bold text-brand-600">{content.faqPromo.eyebrow}</p>
            <h2 className="text-2xl font-bold leading-10 text-secondary-900">{content.faqPromo.title}</h2>
            <p className="mt-4 max-w-lg text-sm leading-8 text-slate-500">
              {content.faqPromo.description}
            </p>
            <Link href="/support" className="mt-7 inline-flex items-center gap-3 rounded-xl bg-secondary-900 px-6 py-3 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:bg-secondary-800">
              {content.faqPromo.buttonLabel}
              <span>←</span>
            </Link>
          </div>
          <div className="relative min-h-72 overflow-hidden bg-brand-50 p-8 sm:p-10">
            <div className="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-brand-100" />
            <div className="absolute left-12 top-10 h-16 w-16 rounded-3xl bg-accent-200/70" />
            <div
              dir="rtl"
              className="relative mr-0 ml-auto mt-5 w-full max-w-sm space-y-3 text-right"
            >
              {content.faqPromo.questions.map((question, index) => (
                <div key={index} className={`rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm ${index === 1 ? "ml-6" : index === 2 ? "ml-12" : ""}`}>
                  <span className="ml-2 font-bold text-brand-600">؟</span>
                  {question}
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
