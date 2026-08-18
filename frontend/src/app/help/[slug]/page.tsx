import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import StaticPageUnavailable from "@/components/static-pages/StaticPageUnavailable";
import {
  getHelpGuideRoute,
  helpGuideRoutes,
  helpPageKeys,
} from "@/lib/help-guides";
import { getStaticPages } from "@/lib/static-pages";

type GuidePageProps = {
  params: Promise<{ slug: string }>;
};

export const dynamicParams = false;
export const dynamic = "force-dynamic";

export function generateStaticParams() {
  return helpGuideRoutes.map((guide) => ({ slug: guide.slug }));
}

export async function generateMetadata({ params }: GuidePageProps): Promise<Metadata> {
  const { slug } = await params;
  const route = getHelpGuideRoute(slug);

  if (!route) return {};
  const pages = await getStaticPages(helpPageKeys);
  if (!pages) return {};
  const page = pages[route.key];
  if (!page.isVisible) return { robots: { index: false, follow: false } };
  const guide = page.content;

  return {
    title: `${guide.title} | گروه صنعتی توانا`,
    description: guide.description,
  };
}

export default async function GuidePage({ params }: GuidePageProps) {
  const { slug } = await params;
  const route = getHelpGuideRoute(slug);
  if (!route) notFound();

  const pages = await getStaticPages(helpPageKeys);
  if (!pages) return <StaticPageUnavailable />;
  const page = pages[route.key];
  if (!page.isVisible) notFound();
  const guide = page.content;
  const sections = page.sections;
  const hasMainContent =
    sections.steps || sections.checklist || sections.faqs || sections.cta;
  const relatedGuides = helpGuideRoutes.filter(
    (item) => item.key !== route.key && pages[item.key].isVisible
  );

  return (
    <div className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:pt-8">
      <nav
        aria-label="مسیر راهنما"
        className="mb-5 flex flex-wrap items-center gap-2 text-xs text-slate-500"
      >
        <Link href="/" className="transition hover:text-brand-700">
          خانه
        </Link>
        <span className="text-slate-300">/</span>
        <Link href="/support" className="transition hover:text-brand-700">
          راهنمای خرید
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-medium text-brand-700">{guide.title}</span>
      </nav>

      {sections.hero && <section className="relative isolate overflow-hidden rounded-[2rem] bg-secondary-900 px-6 py-10 text-white sm:px-10 sm:py-14 lg:px-16 lg:py-16">
        <div className="absolute inset-0 -z-20 bg-[radial-gradient(circle_at_12%_0%,rgba(228,176,40,0.23),transparent_28%),radial-gradient(circle_at_88%_100%,rgba(90,131,73,0.38),transparent_36%)]" />
        <div className="absolute -left-16 top-1/2 -z-10 h-56 w-56 -translate-y-1/2 rounded-full border-[36px] border-white/5" />
        <div className="grid items-center gap-8 lg:grid-cols-[1fr_auto]">
          <div className="max-w-2xl">
            <span className="mb-4 block text-sm font-bold text-accent-300">
              {guide.eyebrow}
            </span>
            <h1 className="text-3xl font-bold leading-[1.5] sm:text-4xl">
              {guide.title}
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-8 text-secondary-100 sm:text-base">
              {guide.intro}
            </p>
          </div>
          <div
            aria-hidden="true"
            className="grid h-28 w-28 place-items-center rounded-[2rem] border border-white/15 bg-white/10 text-5xl shadow-2xl backdrop-blur-sm sm:h-32 sm:w-32 sm:text-6xl"
          >
              {route.icon}
          </div>
        </div>
      </section>}

      {(hasMainContent || sections.aside) && <div className={`mt-8 grid gap-8 lg:items-start ${hasMainContent && sections.aside ? "lg:grid-cols-[1fr_18rem]" : "lg:grid-cols-1"}`}>
        {hasMainContent && <main className="min-w-0 space-y-8">
          {sections.steps && <section className="rounded-[2rem] border border-slate-100 bg-white p-5 sm:p-8">
            <div className="mb-7">
              <p className="mb-2 text-sm font-bold text-brand-600">{guide.sectionLabels.stepsEyebrow}</p>
              <h2 className="text-xl font-bold text-secondary-900 sm:text-2xl">
                {guide.sectionLabels.stepsTitle}
              </h2>
            </div>

            <ol className="relative space-y-4 before:absolute before:bottom-8 before:right-5 before:top-8 before:w-px before:bg-brand-100 sm:before:right-6">
              {guide.steps.map((step, index) => {
                const href = route.stepHrefs[index];
                return (
                <li
                  key={index}
                  className="relative grid grid-cols-[2.5rem_1fr] gap-4 sm:grid-cols-[3rem_1fr] sm:gap-5"
                >
                  <span className="relative z-10 grid h-10 w-10 place-items-center rounded-xl bg-brand-600 text-sm font-bold text-white shadow-sm sm:h-12 sm:w-12">
                    {(index + 1).toLocaleString("fa-IR")}
                  </span>
                  <div className="rounded-2xl bg-slate-50/80 p-5 sm:p-6">
                    <h3 className="font-bold text-secondary-900">{step.title}</h3>
                    <p className="mt-2 text-sm leading-7 text-slate-500">
                      {step.description}
                    </p>
                    {href && step.linkLabel && (
                      <Link
                        href={href}
                        className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-brand-700 transition hover:text-brand-500"
                      >
                        {step.linkLabel}
                        <span>←</span>
                      </Link>
                    )}
                  </div>
                </li>
                );
              })}
            </ol>
          </section>}

          {sections.checklist && <section className="overflow-hidden rounded-[2rem] border border-brand-100 bg-brand-50/60">
            <div className="border-b border-brand-100 bg-white/70 px-6 py-5 sm:px-8">
              <h2 className="text-lg font-bold text-secondary-900">
                {guide.checklist.title}
              </h2>
              {guide.checklist.description && (
                <p className="mt-2 text-sm leading-7 text-slate-500">
                  {guide.checklist.description}
                </p>
              )}
            </div>
            <ul className="grid gap-3 p-5 sm:grid-cols-2 sm:p-8">
              {guide.checklist.items.map((item, index) => (
                <li
                  key={index}
                  className="flex items-start gap-3 rounded-2xl bg-white px-4 py-4 text-sm leading-7 text-slate-600"
                >
                  <span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-100 text-[11px] font-bold text-brand-700">
                    ✓
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>}

          {sections.faqs && <section>
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <p className="mb-1 text-sm font-bold text-brand-600">{guide.sectionLabels.faqEyebrow}</p>
                <h2 className="text-xl font-bold text-secondary-900">
                  {guide.sectionLabels.faqTitle}
                </h2>
              </div>
              <Link
                href="/support"
                className="hidden text-xs font-bold text-brand-700 hover:text-brand-500 sm:block"
              >
                {guide.sectionLabels.allFaqsLabel} ←
              </Link>
            </div>
            <div className="space-y-3">
              {guide.faqs.map((faq, index) => (
                <details
                  key={index}
                  className="group rounded-2xl border border-slate-100 bg-white open:border-brand-200"
                >
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-sm font-bold text-slate-700 marker:content-none sm:px-6">
                    {faq.question}
                    <span className="text-lg font-normal text-brand-600 transition group-open:rotate-45">
                      +
                    </span>
                  </summary>
                  <p className="border-t border-slate-100 px-5 py-4 text-sm leading-8 text-slate-500 sm:px-6">
                    {faq.answer}
                  </p>
                </details>
              ))}
            </div>
          </section>}

          {sections.cta && <section className="relative overflow-hidden rounded-[2rem] bg-brand-700 px-6 py-9 text-white sm:px-9">
            <div className="absolute -bottom-16 -left-10 h-44 w-44 rounded-full border-[30px] border-white/5" />
            <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-bold">{guide.cta.title}</h2>
                <p className="mt-2 text-sm leading-7 text-brand-100">
                  {guide.cta.description}
                </p>
              </div>
              <Link
                href={route.ctaHref}
                className="shrink-0 self-start rounded-xl bg-white px-5 py-3 text-sm font-bold text-brand-700 transition hover:-translate-y-0.5 hover:bg-brand-50 sm:self-auto"
              >
                {guide.cta.label}
              </Link>
            </div>
          </section>}
        </main>}

        {sections.aside && <aside className="space-y-4 lg:sticky lg:top-32">
          <div className="rounded-2xl border border-slate-100 bg-white p-3">
            <h2 className="px-3 pb-3 pt-2 text-xs font-bold text-slate-400">
              {guide.aside.relatedTitle}
            </h2>
            <nav className="space-y-1">
              {relatedGuides.map((item) => (
                <Link
                  key={item.slug}
                  href={`/help/${item.slug}`}
                  className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
                >
                  <span aria-hidden="true">{item.icon}</span>
                  <span className="flex-1">{pages[item.key].content.shortTitle}</span>
                  <span className="text-slate-300">←</span>
                </Link>
              ))}
              <Link
                href="/support"
                className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm text-slate-600 transition hover:bg-brand-50 hover:text-brand-700"
              >
                <span aria-hidden="true">❓</span>
                <span className="flex-1">{guide.aside.faqLabel}</span>
                <span className="text-slate-300">←</span>
              </Link>
            </nav>
          </div>

          <div className="rounded-2xl border border-accent-100 bg-accent-50 p-5">
            <p className="font-bold text-secondary-900">{guide.aside.supportTitle}</p>
            <p className="mt-2 text-xs leading-6 text-slate-500">
              {guide.aside.supportDescription}
            </p>
            <Link
              href="/contact"
              className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-accent-700"
            >
              {guide.aside.supportLabel} <span>←</span>
            </Link>
          </div>
        </aside>}
      </div>}
    </div>
  );
}
