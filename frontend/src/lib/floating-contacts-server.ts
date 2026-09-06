import "server-only";

import { footerFetchOptions } from "@/lib/footer-cache";
import { isContactButton, type FloatingContactButton } from "@/lib/floating-contacts";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export async function getFloatingContactButtons(): Promise<FloatingContactButton[]> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/site-settings/floating-contact-buttons`, {
      // Share the library's tag so replacing a selected footer icon invalidates contacts too.
      ...footerFetchOptions(process.env.NODE_ENV),
      signal: AbortSignal.timeout(5000),
    });
    const json = await response.json();
    if (!response.ok || !json?.ok || !Array.isArray(json.data?.buttons)) return [];
    return json.data.buttons.filter(isContactButton);
  } catch {
    return [];
  }
}
