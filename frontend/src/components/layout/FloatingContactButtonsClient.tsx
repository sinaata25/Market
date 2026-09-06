"use client";

import { usePathname } from "next/navigation";
import ContactIcon from "@/components/layout/ContactIcon";
import { contactIconName, contactLinkAttributes, groupContactButtons, isStorefrontPath, type FloatingContactButton } from "@/lib/floating-contacts";

export function ContactButtonStacks({ buttons }: { buttons: FloatingContactButton[] }) {
  const groups = groupContactButtons(buttons);
  if (!groups["bottom-right"].length && !groups["bottom-left"].length) return null;
  return (
    <>
      {Object.entries(groups).map(([position, items]) => items.length > 0 && (
        <nav key={position} data-floating-contacts={position} aria-label={position === "bottom-right" ? "راه‌های تماس، سمت راست" : "راه‌های تماس، سمت چپ"} className="floating-contact-stack">
          {items.map((button) => (
            <a key={button.id} {...contactLinkAttributes(button)} className="floating-contact-button">
              <ContactIcon image={button.icon} name={contactIconName(button)} />
            </a>
          ))}
        </nav>
      ))}
    </>
  );
}

export default function FloatingContactButtonsClient({ buttons }: { buttons: FloatingContactButton[] }) {
  const pathname = usePathname();
  if (!isStorefrontPath(pathname)) return null;
  return <ContactButtonStacks buttons={buttons} />;
}
