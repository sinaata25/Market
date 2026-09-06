import { CONTACT_ICONS } from "@/lib/floating-contacts";

// All built-in artwork lives here; arbitrary platforms use the link fallback.
const PATHS: Record<string, string> = {
  phone: "M7 3H4a1 1 0 0 0-1 1c0 9.4 7.6 17 17 17a1 1 0 0 0 1-1v-3l-5-2-2 2a14 14 0 0 1-7-7l2-2-2-5Z",
  whatsapp: "M20.5 11.5a8.5 8.5 0 0 1-12.7 7.4L3 21l1.8-5a8.5 8.5 0 1 1 15.7-4.5ZM8 7.5l1.5 2-1 1a8 8 0 0 0 4 4l1-1 2 1.5M8 7.5c-2 4 4.5 10.5 7.5 7.5",
  send: "m3 10 18-7-7 18-4-7-7-4Zm7 4L21 3",
  instagram: "M7 3h10a4 4 0 0 1 4 4v10a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4-4Zm9 9a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm1-5h.01",
  chat: "M21 11a8 8 0 0 1-8 8H8l-5 3V11a9 9 0 0 1 18 0ZM7 11h10M7 15h6",
  email: "M3 5h18v14H3V5Zm0 1 9 7 9-7",
  link: "m10 13 4-4M8 15l-1 1a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0m2 10a3.5 3.5 0 0 0 5 0l4-4a3.5 3.5 0 0 0-5-5l-1 1",
  cube: "m12 2 9 5v10l-9 5-9-5V7l9-5ZM3 7l9 5 9-5M12 12v10",
};

export default function ContactIcon({ image, name }: { image: string | null; name: string }) {
  if (image) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={image} alt="" aria-hidden="true" width={28} height={28} className="size-7 object-contain" />;
  }
  const glyph = (Object.hasOwn(CONTACT_ICONS, name) ? CONTACT_ICONS[name] : CONTACT_ICONS.custom).glyph;
  const path = PATHS[glyph];
  if (!path) return <span aria-hidden="true" className="text-xl font-bold" dir="auto">{glyph}</span>;
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" className="size-7">
      <path d={path} />
    </svg>
  );
}
