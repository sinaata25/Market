"use client";

import SpecificationKeyCombobox from "@/components/admin/SpecificationKeyCombobox";
import {
  newSpecificationDraft,
  type SpecificationDraft,
  type SpecificationDraftError,
} from "@/components/admin/specification-types";

export default function SpecificationEditor({
  rows,
  errors,
  onChange,
  disabled = false,
}: {
  rows: SpecificationDraft[];
  errors: Record<string, SpecificationDraftError>;
  onChange: (rows: SpecificationDraft[]) => void;
  disabled?: boolean;
}) {
  function updateRow(
    clientId: string,
    update: Partial<Omit<SpecificationDraft, "clientId">>
  ) {
    onChange(
      rows.map((row) =>
        row.clientId === clientId ? { ...row, ...update } : row
      )
    );
  }

  function moveRow(index: number, direction: -1 | 1) {
    const destination = index + direction;
    if (destination < 0 || destination >= rows.length) return;
    const next = [...rows];
    [next[index], next[destination]] = [next[destination], next[index]];
    onChange(next);
  }

  return (
    <fieldset className="border-t border-slate-100 pt-5">
      <legend className="px-2 text-sm font-bold text-slate-700">
        مشخصات محصول
      </legend>
      <p className="mb-4 mt-1 text-[11px] leading-6 text-slate-400">
        مشخصه‌های موجود را جستجو کنید یا همان‌جا یک مشخصه جدید و قابل استفاده برای
        همه محصولات بسازید.
      </p>

      {rows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-4 py-6 text-center text-xs text-slate-400">
          هنوز مشخصه‌ای برای این محصول اضافه نشده است.
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((row, index) => {
            const rowError = errors[row.clientId] ?? {};
            const excludedIds = rows
              .filter((item) => item.clientId !== row.clientId && item.key)
              .map((item) => item.key!.id);
            return (
              <div
                key={row.clientId}
                className="rounded-xl border border-slate-100 bg-slate-50/60 p-3"
              >
                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)_auto] sm:items-start">
                  <div>
                    <label
                      htmlFor={`specification-key-${row.clientId}`}
                      className="mb-1.5 block text-xs font-medium text-slate-600"
                    >
                      مشخصه {index + 1}
                    </label>
                    <SpecificationKeyCombobox
                      id={`specification-key-${row.clientId}`}
                      value={row.key}
                      excludedIds={excludedIds}
                      onChange={(key) => updateRow(row.clientId, { key })}
                      hasError={Boolean(rowError.key)}
                      disabled={disabled}
                    />
                    {rowError.key && (
                      <p className="mt-1.5 text-[11px] text-red-500">
                        {rowError.key}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor={`specification-value-${row.clientId}`}
                      className="mb-1.5 block text-xs font-medium text-slate-600"
                    >
                      مقدار این محصول
                    </label>
                    <input
                      id={`specification-value-${row.clientId}`}
                      value={row.value}
                      maxLength={500}
                      disabled={disabled}
                      aria-invalid={Boolean(rowError.value) || undefined}
                      onChange={(event) =>
                        updateRow(row.clientId, { value: event.target.value })
                      }
                      className={`w-full rounded-xl border bg-white px-3 py-2.5 text-sm outline-none transition disabled:cursor-not-allowed disabled:opacity-60 ${
                        rowError.value
                          ? "border-red-300 focus:border-red-400"
                          : "border-slate-200 focus:border-brand-400"
                      }`}
                      placeholder="مثلاً ۲۵ × ۲۰ × ۲۰ سانتی‌متر"
                    />
                    {rowError.value && (
                      <p className="mt-1.5 text-[11px] text-red-500">
                        {rowError.value}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 sm:pt-7">
                    <button
                      type="button"
                      disabled={disabled || index === 0}
                      onClick={() => moveRow(index, -1)}
                      className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500 transition hover:border-brand-300 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-30"
                      title="انتقال به بالا"
                      aria-label={`انتقال مشخصه ${index + 1} به بالا`}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      disabled={disabled || index === rows.length - 1}
                      onClick={() => moveRow(index, 1)}
                      className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-sm text-slate-500 transition hover:border-brand-300 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-30"
                      title="انتقال به پایین"
                      aria-label={`انتقال مشخصه ${index + 1} به پایین`}
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() =>
                        onChange(
                          rows.filter((item) => item.clientId !== row.clientId)
                        )
                      }
                      className="h-9 rounded-lg border border-red-100 bg-white px-2.5 text-xs text-red-500 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      حذف
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <button
        type="button"
        disabled={disabled}
        onClick={() => onChange([...rows, newSpecificationDraft()])}
        className="mt-3 rounded-xl border border-dashed border-brand-300 bg-brand-50/40 px-4 py-2.5 text-xs font-medium text-brand-700 transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
      >
        + افزودن مشخصه
      </button>
    </fieldset>
  );
}
