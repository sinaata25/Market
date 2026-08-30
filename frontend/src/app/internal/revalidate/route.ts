import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { FOOTER_CACHE_TAG } from "@/lib/footer";

/**
 * باطل‌کردن کش داده‌های سرور به‌درخواست بک‌اند.
 *
 * جنگو بعد از هر تغییر مدیر در فوتر این مسیر را صدا می‌زند. مسیر عمداً زیر
 * /api نیست، چون همه‌ی /api/* با rewrite به جنگو پروکسی می‌شوند.
 */
const ALLOWED_TAGS = new Set([FOOTER_CACHE_TAG]);

function secretMatches(received: string | null): boolean {
  const expected = process.env.FRONTEND_REVALIDATE_SECRET ?? "";
  if (!expected || !received) return false;
  const a = Buffer.from(received);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}

export async function POST(request: Request) {
  if (!secretMatches(request.headers.get("x-revalidate-secret"))) {
    return Response.json({ ok: false, error: "forbidden" }, { status: 403 });
  }

  const body = await request.json().catch(() => null);
  const tag = typeof body?.tag === "string" ? body.tag : "";
  if (!ALLOWED_TAGS.has(tag)) {
    return Response.json({ ok: false, error: "unknown tag" }, { status: 422 });
  }

  revalidateTag(tag, "max");
  return Response.json({ ok: true, data: { revalidated: tag } });
}
