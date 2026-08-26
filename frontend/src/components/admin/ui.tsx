"use client";

// اجزای مشترک داشبورد مدیریت

export const STATUS_FA: Record<string, { label: string; className: string }> = {
  PENDING: { label: "در انتظار پرداخت", className: "bg-amber-50 text-amber-600" },
  PAID: { label: "پرداخت شده", className: "bg-blue-50 text-blue-600" },
  SHIPPED: { label: "ارسال شده", className: "bg-indigo-50 text-indigo-600" },
  DELIVERED: { label: "تحویل شده", className: "bg-emerald-50 text-emerald-600" },
  CANCELED: { label: "لغو شده", className: "bg-red-50 text-red-500" },
};

export function faNum(n: number) {
  return n.toLocaleString("fa-IR");
}

export function faDate(iso: string) {
  return new Date(iso).toLocaleDateString("fa-IR", {
    month: "short",
    day: "numeric",
  });
}

export function faDateTime(iso: string) {
  return new Date(iso).toLocaleString("fa-IR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS_FA[status] ?? STATUS_FA.PENDING;
  return (
    <span
      className={`inline-block rounded-lg px-2.5 py-1 text-[11px] font-medium ${s.className}`}
    >
      {s.label}
    </span>
  );
}

export function StatCard({
  icon,
  label,
  value,
  sub,
  accent = "bg-brand-50 text-brand-700",
}: {
  icon: string;
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="@container/stat flex flex-col gap-3 rounded-2xl border border-slate-100 bg-white p-4 @min-[15rem]/stat:flex-row @min-[15rem]/stat:items-center @min-[15rem]/stat:gap-4 @min-[15rem]/stat:p-5">
      <span
        className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl text-xl @min-[15rem]/stat:h-12 @min-[15rem]/stat:w-12 @min-[15rem]/stat:text-2xl ${accent}`}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="mt-1 text-base font-bold text-slate-800 font-num @min-[15rem]/stat:text-lg">
          {value}
        </p>
        {sub && <p className="mt-0.5 text-[11px] leading-5 text-slate-400">{sub}</p>}
      </div>
    </div>
  );
}

export function Pager({
  page,
  pages,
  onPage,
}: {
  page: number;
  pages: number;
  onPage: (p: number) => void;
}) {
  if (pages <= 1) return null;

  // روی موبایل جا برای ده‌ها دکمه نیست؛ فقط پنجره‌ای around صفحه‌ی جاری
  // به‌همراه صفحه‌ی اول و آخر نمایش داده می‌شود.
  const nearby = new Set([1, pages, page, page - 1, page + 1]);
  const shown = [...nearby].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);

  const cell =
    "grid h-9 min-w-9 place-items-center rounded-lg border px-2 text-xs font-num transition sm:h-8 sm:min-w-8";

  return (
    <nav
      aria-label="صفحه‌بندی"
      className="mt-4 flex flex-wrap items-center justify-center gap-1.5"
    >
      <button
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
        aria-label="صفحه‌ی قبل"
        className={`${cell} border-slate-200 bg-white text-slate-600 hover:border-brand-400 disabled:opacity-40 disabled:hover:border-slate-200`}
      >
        ›
      </button>

      {shown.map((n, i) => (
        <span key={n} className="flex items-center gap-1.5">
          {i > 0 && shown[i - 1] !== n - 1 && (
            <span className="px-0.5 text-xs text-slate-300">…</span>
          )}
          <button
            onClick={() => onPage(n)}
            aria-current={n === page ? "page" : undefined}
            className={`${cell} ${
              n === page
                ? "border-brand-600 bg-brand-600 font-bold text-white"
                : "border-slate-200 bg-white text-slate-600 hover:border-brand-400"
            }`}
          >
            {faNum(n)}
          </button>
        </span>
      ))}

      <button
        onClick={() => onPage(page + 1)}
        disabled={page >= pages}
        aria-label="صفحه‌ی بعد"
        className={`${cell} border-slate-200 bg-white text-slate-600 hover:border-brand-400 disabled:opacity-40 disabled:hover:border-slate-200`}
      >
        ‹
      </button>
    </nav>
  );
}

export function EmptyRow({ colSpan, text }: { colSpan: number; text: string }) {
  return (
    <tr>
      <td
        colSpan={colSpan}
        className="px-4 py-10 text-center text-sm text-slate-400"
      >
        {text}
      </td>
    </tr>
  );
}
