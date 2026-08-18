export const STATIC_PAGE_KEYS = [
  "about",
  "contact",
  "support",
  "shipping",
  "returns",
  "how-to-order",
  "track-order",
  "warranty",
] as const;

export type StaticPageKey = (typeof STATIC_PAGE_KEYS)[number];

type Pair<T> = readonly [T, T];
type Triple<T> = readonly [T, T, T];
type Quad<T> = readonly [T, T, T, T];
type Quint<T> = readonly [T, T, T, T, T];

export type AboutPageContent = {
  hero: {
    badge: string;
    title: string;
    accent: string;
    intro: string;
    primaryLabel: string;
    secondaryLabel: string;
    captionEyebrow: string;
    captionTitle: string;
  };
  story: {
    eyebrow: string;
    title: string;
    paragraphs: Pair<string>;
  };
  values: {
    eyebrow: string;
    title: string;
    items: Triple<{ title: string; description: string }>;
  };
  journey: {
    eyebrow: string;
    title: string;
    description: string;
    items: Triple<{ title: string; description: string }>;
  };
  closing: {
    eyebrow: string;
    title: string;
    description: string;
    primaryLabel: string;
    secondaryLabel: string;
  };
};

type ContactWay = {
  eyebrow: string;
  title: string;
  description: string;
};

export type ContactPageContent = {
  hero: {
    badge: string;
    title: string;
    accent: string;
    suffix: string;
    intro: string;
  };
  ways: readonly [
    ContactWay & { label: string; phoneNumber: string },
    ContactWay & { label: string },
    ContactWay & { label: string },
  ];
  topics: {
    eyebrow: string;
    title: string;
    description: string;
    items: Triple<{ title: string; text: string }>;
  };
  faqPromo: {
    eyebrow: string;
    title: string;
    description: string;
    buttonLabel: string;
    questions: Triple<string>;
  };
};

export type FaqItemContent = { question: string; answer: string };

export type SupportPageContent = {
  hero: {
    title: string;
    description: string;
    searchPlaceholder: string;
  };
  sidebarTitle: string;
  noResults: { beforeQuery: string; afterQuery: string };
  groups: readonly [
    { title: string; items: Triple<FaqItemContent> },
    { title: string; items: Triple<FaqItemContent> },
    { title: string; items: Triple<FaqItemContent> },
    { title: string; items: Pair<FaqItemContent> },
    { title: string; items: Pair<FaqItemContent> },
    { title: string; items: Pair<FaqItemContent> },
  ];
  contact: {
    title: string;
    description: string;
    phoneLabel: string;
    onlineLabel: string;
    onlineUrl: string;
  };
};

export type HelpStepContent = {
  title: string;
  description: string;
  linkLabel?: string;
};

type HelpGuideContent<
  Steps extends readonly HelpStepContent[],
  ChecklistItems extends readonly string[],
> = {
  title: string;
  shortTitle: string;
  eyebrow: string;
  description: string;
  intro: string;
  sectionLabels: {
    stepsEyebrow: string;
    stepsTitle: string;
    faqEyebrow: string;
    faqTitle: string;
    allFaqsLabel: string;
  };
  aside: {
    relatedTitle: string;
    faqLabel: string;
    supportTitle: string;
    supportDescription: string;
    supportLabel: string;
  };
  steps: Steps;
  checklist: {
    title: string;
    description?: string;
    items: ChecklistItems;
  };
  faqs: Pair<{ question: string; answer: string }>;
  cta: { title: string; description: string; label: string };
};

export type HowToOrderPageContent = HelpGuideContent<
  Quint<HelpStepContent>,
  Quad<string>
>;
export type TrackOrderPageContent = HelpGuideContent<
  Triple<HelpStepContent>,
  Quint<string>
>;
export type WarrantyPageContent = HelpGuideContent<
  Triple<HelpStepContent>,
  Quad<string>
>;
export type ShippingPageContent = HelpGuideContent<
  Quad<HelpStepContent>,
  Quad<string>
>;
export type ReturnsPageContent = HelpGuideContent<
  Quad<HelpStepContent>,
  Quad<string>
>;

export type StaticPageContentMap = {
  about: AboutPageContent;
  contact: ContactPageContent;
  support: SupportPageContent;
  shipping: ShippingPageContent;
  returns: ReturnsPageContent;
  "how-to-order": HowToOrderPageContent;
  "track-order": TrackOrderPageContent;
  warranty: WarrantyPageContent;
};

export type StaticPageSectionMap = {
  about: "hero" | "story" | "values" | "journey" | "closing";
  contact: "hero" | "ways" | "topics" | "faq-promo";
  support:
    | "hero"
    | "faq-order"
    | "faq-payment"
    | "faq-shipping"
    | "faq-return"
    | "faq-warranty"
    | "faq-account"
    | "contact";
  shipping: "hero" | "steps" | "checklist" | "faqs" | "cta" | "aside";
  returns: "hero" | "steps" | "checklist" | "faqs" | "cta" | "aside";
  "how-to-order":
    | "hero"
    | "steps"
    | "checklist"
    | "faqs"
    | "cta"
    | "aside";
  "track-order":
    | "hero"
    | "steps"
    | "checklist"
    | "faqs"
    | "cta"
    | "aside";
  warranty: "hero" | "steps" | "checklist" | "faqs" | "cta" | "aside";
};

export type ManagedStaticPage<K extends StaticPageKey> = {
  key: K;
  isVisible: boolean;
  sections: Record<StaticPageSectionMap[K], boolean>;
  content: StaticPageContentMap[K];
};

export type StaticPageRecordMap = {
  [K in StaticPageKey]: ManagedStaticPage<K>;
};

export type HelpPageKey = Exclude<
  StaticPageKey,
  "about" | "contact" | "support"
>;
