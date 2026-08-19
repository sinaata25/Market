import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import StaticPageUnavailable from "@/components/static-pages/StaticPageUnavailable";
import { getStaticPage } from "@/lib/static-pages";

export const metadata: Metadata = {
  title: "درباره ما | گروه صنعتی توانا",
  description:
    "با گروه صنعتی توانا، مسیر انتخاب و خرید مطمئن ابزارآلات و ادوات کشاورزی، بیشتر آشنا شوید.",
};

export const dynamic = "force-dynamic";

const valueIcons = ["shield", "sprout", "chat"] as const;
const journeyNumbers = ["۰۱", "۰۲", "۰۳"] as const;

function LineIcon({ name }: { name: (typeof valueIcons)[number] }) {
  if (name === "shield") {
    return (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-7 w-7">
        <path d="M12 3 5.5 5.5v5.8c0 4.2 2.7 7.9 6.5 9.2 3.8-1.3 6.5-5 6.5-9.2V5.5L12 3Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
        <path d="m9 12 2 2 4-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (name === "sprout") {
    return (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-7 w-7">
        <path d="M12 20v-9M12 13c-4.6 0-7-2.6-7-7 4.6 0 7 2.6 7 7Zm0 3c4.6 0 7-2.6 7-7-4.6 0-7 2.6-7 7Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-7 w-7">
      <path d="M20 11.5a7.5 7.5 0 0 1-8 7.5 9.4 9.4 0 0 1-3.4-.7L4 20l1.5-4A7.4 7.4 0 0 1 4 11.5 7.5 7.5 0 0 1 12 4a7.5 7.5 0 0 1 8 7.5Z" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M8.5 11.5h.01M12 11.5h.01M15.5 11.5h.01" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export default async function AboutPage() {
  const page = await getStaticPage("about");
  if (!page) return <StaticPageUnavailable />;
  if (!page.isVisible) notFound();
  const { content, sections } = page;

  return (
    <div className="overflow-hidden">
      <div className="mx-auto max-w-7xl px-4 pb-16 pt-6 sm:pt-8">
        <nav aria-label="مسیر راهنما" className="mb-5 flex items-center gap-2 text-xs text-slate-500">
          <Link href="/" className="transition hover:text-brand-700">
            خانه
          </Link>
          <span className="text-slate-300">/</span>
          <span className="font-medium text-brand-700">درباره ما</span>
        </nav>

        {sections.hero && <section className="relative isolate overflow-hidden rounded-[2rem] bg-secondary-900 px-6 py-10 text-white shadow-[0_24px_80px_-45px_rgba(20,36,79,0.8)] sm:px-10 sm:py-14 lg:px-16 lg:py-20">
          <div className="absolute inset-0 -z-20 bg-[radial-gradient(circle_at_10%_0%,rgba(228,176,40,0.24),transparent_30%),radial-gradient(circle_at_90%_100%,rgba(117,153,102,0.35),transparent_38%)]" />
          <div className="absolute -left-20 top-10 -z-10 h-72 w-72 rounded-full border border-white/10" />
          <div className="absolute -left-10 top-20 -z-10 h-52 w-52 rounded-full border border-white/10" />

          <div className="grid items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
            <div>
              <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs text-secondary-100 backdrop-blur-sm">
                <span className="h-2 w-2 rounded-full bg-accent-400" />
                {content.hero.badge}
              </span>
              <h1 className="max-w-2xl text-3xl font-bold leading-[1.55] sm:text-4xl lg:text-5xl">
                {content.hero.title}
                {" "}
                <span className="text-accent-300">{content.hero.accent}</span>
              </h1>
              <p className="mt-5 max-w-xl text-sm leading-8 text-secondary-100 sm:text-base sm:leading-9">
                {content.hero.intro}
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href="/category/garden-tools" className="rounded-xl bg-accent-400 px-6 py-3 text-sm font-bold text-secondary-900 transition hover:-translate-y-0.5 hover:bg-accent-300">
                  {content.hero.primaryLabel}
                </Link>
                <Link href="/support" className="rounded-xl border border-white/20 bg-white/5 px-6 py-3 text-sm font-medium text-white transition hover:bg-white/10">
                  {content.hero.secondaryLabel}
                </Link>
              </div>
            </div>

            <div className="relative mx-auto grid h-72 w-full max-w-sm place-items-center sm:h-80">
              <div className="absolute h-64 w-64 rounded-full bg-brand-500/20 blur-2xl" />
              <div className="absolute h-60 w-60 rotate-6 rounded-[3rem] border border-white/10 bg-white/5 backdrop-blur-sm" />
              <div className="relative grid h-48 w-48 place-items-center rounded-[2.5rem] bg-white shadow-2xl shadow-black/20 sm:h-56 sm:w-56">
                <Image src="/brand/logo.png" alt="نشان گروه صنعتی توانا" width={160} height={160} priority className="h-36 w-36 object-contain sm:h-40 sm:w-40" />
              </div>
              <div className="absolute bottom-3 right-0 rounded-2xl border border-white/10 bg-white/95 px-4 py-3 text-secondary-900 shadow-xl sm:right-2">
                <span className="block text-[10px] text-slate-400">{content.hero.captionEyebrow}</span>
                <span className="text-sm font-bold">{content.hero.captionTitle}</span>
              </div>
            </div>
          </div>
        </section>}

        {sections.story && <section className="grid gap-8 py-16 lg:grid-cols-[0.85fr_1.15fr] lg:items-center lg:gap-20 lg:py-24">
          <div>
            <p className="mb-3 text-sm font-bold text-brand-600">{content.story.eyebrow}</p>
            <h2 className="text-2xl font-bold leading-10 text-secondary-900 sm:text-3xl">
              {content.story.title}
            </h2>
          </div>
          <div className="space-y-5 text-sm leading-8 text-slate-600 sm:text-base sm:leading-9">
            {content.story.paragraphs.map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
        </section>}

        {sections.values && <section className="rounded-[2rem] border border-brand-100 bg-white p-5 sm:p-8 lg:p-10">
          <div className="mb-8 max-w-xl">
            <p className="mb-2 text-sm font-bold text-brand-600">{content.values.eyebrow}</p>
            <h2 className="text-2xl font-bold text-secondary-900">{content.values.title}</h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {content.values.items.map((value, index) => (
              <article key={index} className="group rounded-2xl border border-slate-100 bg-slate-50/70 p-6 transition hover:-translate-y-1 hover:border-brand-200 hover:bg-brand-50/50">
                <div className="mb-7 flex items-start justify-between">
                  <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-100 text-brand-700 transition group-hover:bg-brand-600 group-hover:text-white">
                    <LineIcon name={valueIcons[index]} />
                  </span>
                  <span className="font-num text-xs text-slate-300">
                    {(index + 1).toLocaleString("fa-IR", {
                      minimumIntegerDigits: 2,
                    })}
                  </span>
                </div>
                <h3 className="mb-3 font-bold text-secondary-900">{value.title}</h3>
                <p className="text-sm leading-7 text-slate-500">{value.description}</p>
              </article>
            ))}
          </div>
        </section>}

        {sections.journey && <section className="py-16 lg:py-24">
          <div className="grid gap-8 lg:grid-cols-[0.7fr_1.3fr] lg:gap-16">
            <div>
              <p className="mb-3 text-sm font-bold text-brand-600">{content.journey.eyebrow}</p>
              <h2 className="text-2xl font-bold leading-10 text-secondary-900 sm:text-3xl">
                {content.journey.title}
              </h2>
              <p className="mt-4 max-w-md text-sm leading-8 text-slate-500">
                {content.journey.description}
              </p>
            </div>
            <ol className="space-y-3">
              {content.journey.items.map((item, index) => (
                <li key={journeyNumbers[index]} className="grid grid-cols-[3rem_1fr] gap-4 rounded-2xl border border-slate-200/70 bg-white p-5 sm:grid-cols-[4rem_1fr] sm:p-6">
                  <span className="font-num pt-0.5 text-xl font-bold text-accent-600">{journeyNumbers[index]}</span>
                  <div>
                    <h3 className="font-bold text-secondary-900">{item.title}</h3>
                    <p className="mt-2 text-sm leading-7 text-slate-500">{item.description}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>}

        {sections.closing && <section className="relative overflow-hidden rounded-[2rem] bg-brand-700 px-6 py-10 text-center text-white sm:px-10 sm:py-12">
          <div className="absolute -right-12 -top-20 h-52 w-52 rounded-full border-[35px] border-white/5" />
          <div className="relative mx-auto max-w-2xl">
            <p className="mb-3 text-sm font-bold text-brand-100">{content.closing.eyebrow}</p>
            <h2 className="text-2xl font-bold leading-10 sm:text-3xl">{content.closing.title}</h2>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-7 text-brand-100">
              {content.closing.description}
            </p>
            <div className="mt-7 flex flex-wrap justify-center gap-3">
              <Link href="/" className="rounded-xl bg-white px-6 py-3 text-sm font-bold text-brand-700 transition hover:bg-brand-50">{content.closing.primaryLabel}</Link>
              <Link href="/support" className="rounded-xl border border-white/20 px-6 py-3 text-sm font-medium transition hover:bg-white/10">{content.closing.secondaryLabel}</Link>
            </div>
          </div>
        </section>}
      </div>
    </div>
  );
}
