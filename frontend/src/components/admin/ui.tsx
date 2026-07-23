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
    <div className="flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-5">
      <span
        className={`grid h-12 w-12 shrink-0 place-items-center rounded-xl text-2xl ${accent}`}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xs text-slate-400">{label}</p>
        <p className="mt-1 truncate text-lg font-bold text-slate-800 font-num">
          {value}
        </p>
        {sub && <p className="mt-0.5 text-[11px] text-slate-400">{sub}</p>}
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
  return (
    <div className="mt-4 flex items-center justify-center gap-1.5">
      {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
        <button
          key={n}
          onClick={() => onPage(n)}
          className={`grid h-8 w-8 place-items-center rounded-lg border text-xs font-num transition ${
            n === page
              ? "border-brand-600 bg-brand-600 font-bold text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-brand-400"
          }`}
        >
          {faNum(n)}
        </button>
      ))}
    </div>
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
