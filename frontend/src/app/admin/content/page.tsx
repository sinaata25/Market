"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { faDateTime } from "@/components/admin/ui";
import { api } from "@/lib/client-api";

type PageSummary = {
  key: string;
  label: string;
  path: string;
  isVisible: boolean;
  updatedAt: string | null;
  updatedBy: string | null;
};

type ContentSection = {
  id: string;
  label: string;
  visible: boolean;
};

type ContentField = {
  id: string;
  label: string;
  group: string;
  control: "text" | "textarea" | "email" | "tel" | "url";
  required: boolean;
  maxLength: number;
  rows?: number;
  dir?: "rtl" | "ltr";
  help?: string;
  value: string;
};

type ContentPage = PageSummary & {
  sections: ContentSection[];
  fields: ContentField[];
};

type FieldValues = Record<string, string>;
type ContentErrorData = { fieldErrors?: Record<string, string> };

const ALLOWED_CONTROLS = ["text", "textarea", "email", "tel", "url"] as const;

const INPUT_CLASS =
  "w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none transition focus:border-brand-400 focus:bg-white disabled:cursor-wait disabled:opacity-60";
const UNSAVED_MESSAGE =
  "تغییرات این صفحه ذخیره نشده است. بدون ذخیره از صفحه خارج شوید؟";

function fieldValues(fields: ContentField[]): FieldValues {
  return Object.fromEntries(fields.map((field) => [field.id, field.value]));
}

function sectionValues(sections: ContentSection[]): Record<string, boolean> {
  return Object.fromEntries(
    sections.map((section) => [section.id, section.visible])
  );
}

function sameValues<T extends string | boolean>(
  left: Record<string, T>,
  right: Record<string, T>
): boolean {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  return (
    leftKeys.length === rightKeys.length &&
    leftKeys.every((key) => left[key] === right[key])
  );
}

function inputDirection(field: ContentField): "rtl" | "ltr" {
  if (field.dir) return field.dir;
  return ["email", "tel", "url"].includes(field.control) ? "ltr" : "rtl";
}

function safeControl(control: ContentField["control"]): ContentField["control"] {
  return ALLOWED_CONTROLS.includes(control) ? control : "text";
}

export default function AdminContentPage() {
  const router = useRouter();
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [page, setPage] = useState<ContentPage | null>(null);
  const [values, setValues] = useState<FieldValues>({});
  const [initialValues, setInitialValues] = useState<FieldValues>({});
  const [pageVisible, setPageVisible] = useState(true);
  const [initialPageVisible, setInitialPageVisible] = useState(true);
  const [sectionVisibility, setSectionVisibility] = useState<
    Record<string, boolean>
  >({});
  const [initialSectionVisibility, setInitialSectionVisibility] = useState<
    Record<string, boolean>
  >({});
  const [listLoading, setListLoading] = useState(true);
  const [pageLoading, setPageLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [listError, setListError] = useState("");
  const [pageError, setPageError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [detailReload, setDetailReload] = useState(0);
  const listRequest = useRef(0);
  const pageRequest = useRef(0);

  const dirty = useMemo(
    () =>
      Boolean(page) &&
      (pageVisible !== initialPageVisible ||
        !sameValues(values, initialValues) ||
        !sameValues(sectionVisibility, initialSectionVisibility)),
    [
      initialPageVisible,
      initialSectionVisibility,
      initialValues,
      page,
      pageVisible,
      sectionVisibility,
      values,
    ]
  );

  const groups = useMemo(() => {
    const grouped: { label: string; fields: ContentField[] }[] = [];
    const indexes = new Map<string, number>();

    for (const field of page?.fields ?? []) {
      let index = indexes.get(field.group);
      if (index === undefined) {
        index = grouped.length;
        indexes.set(field.group, index);
        grouped.push({ label: field.group, fields: [] });
      }
      grouped[index].fields.push(field);
    }

    return grouped;
  }, [page]);

  const loadPages = useCallback(async (initial = false) => {
    const requestId = ++listRequest.current;
    const result = await api.get<{ pages: PageSummary[] }>(
      "/api/admin/content/pages"
    );
    if (requestId !== listRequest.current) return;

    if (!result.ok || !result.data) {
      setListError(result.error ?? "دریافت فهرست صفحات انجام نشد");
      setListLoading(false);
      return;
    }

    const nextPages = result.data.pages;
    setPages(nextPages);
    setListError("");
    if (initial) {
      setPageLoading(Boolean(nextPages.length));
      setSelectedKey(nextPages[0]?.key ?? null);
    } else {
      setSelectedKey((current) => {
        if (current && nextPages.some((item) => item.key === current)) {
          return current;
        }
        return nextPages[0]?.key ?? null;
      });
    }
    setListLoading(false);
  }, []);

  useEffect(() => {
    const loadTimer = window.setTimeout(() => void loadPages(true), 0);
    return () => {
      window.clearTimeout(loadTimer);
      listRequest.current += 1;
    };
  }, [loadPages]);

  useEffect(() => {
    if (!selectedKey) return;

    const requestId = ++pageRequest.current;
    api
      .get<{ page: ContentPage }>(
        `/api/admin/content/pages/${encodeURIComponent(selectedKey)}`
      )
      .then((result) => {
        if (requestId !== pageRequest.current) return;
        if (!result.ok || !result.data) {
          setPage(null);
          setValues({});
          setInitialValues({});
          setPageError(result.error ?? "دریافت محتوای صفحه انجام نشد");
          setPageLoading(false);
          return;
        }

        const nextPage = result.data.page;
        const nextValues = fieldValues(nextPage.fields);
        const nextSections = sectionValues(nextPage.sections);
        setPage(nextPage);
        setValues(nextValues);
        setInitialValues(nextValues);
        setPageVisible(nextPage.isVisible);
        setInitialPageVisible(nextPage.isVisible);
        setSectionVisibility(nextSections);
        setInitialSectionVisibility(nextSections);
        setFieldErrors({});
        setPageLoading(false);
      });

    return () => {
      pageRequest.current += 1;
    };
  }, [detailReload, selectedKey]);

  useEffect(() => {
    if (!dirty) return;
    const preventUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener("beforeunload", preventUnload);
    return () => window.removeEventListener("beforeunload", preventUnload);
  }, [dirty]);

  useEffect(() => {
    if (!dirty) return;

    const preventClientNavigation = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const target = event.target;
      const navigationTarget =
        target instanceof Element
          ? target.closest<HTMLElement>("a[href], [data-admin-navigation]")
          : null;
      if (!navigationTarget) return;

      const anchor =
        navigationTarget instanceof HTMLAnchorElement
          ? navigationTarget
          : null;
      if (
        anchor &&
        (anchor.target === "_blank" || anchor.hasAttribute("download"))
      ) {
        return;
      }

      if (anchor) {
        const destination = new URL(anchor.href, window.location.href);
        if (
          destination.origin !== window.location.origin ||
          destination.href === window.location.href
        ) {
          return;
        }
      }

      if (!window.confirm(UNSAVED_MESSAGE)) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    };

    document.addEventListener("click", preventClientNavigation, true);
    return () =>
      document.removeEventListener("click", preventClientNavigation, true);
  }, [dirty]);

  useEffect(() => {
    const firstFieldId = Object.keys(fieldErrors)[0];
    if (!firstFieldId) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(`content-field-${firstFieldId}`)?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [fieldErrors]);

  function selectPage(key: string) {
    if (key === selectedKey || saving) return;
    if (dirty && !window.confirm(UNSAVED_MESSAGE)) {
      return;
    }
    setPage(null);
    setValues({});
    setInitialValues({});
    setSectionVisibility({});
    setInitialSectionVisibility({});
    setPageLoading(true);
    setPageError("");
    setFieldErrors({});
    setMessage("");
    setSelectedKey(key);
  }

  function updateField(id: string, value: string) {
    setValues((current) => ({ ...current, [id]: value }));
    setMessage("");
    setPageError("");
    setFieldErrors({});
  }

  function updatePageVisibility(visible: boolean) {
    setPageVisible(visible);
    setMessage("");
    setPageError("");
    setFieldErrors({});
  }

  function updateSectionVisibility(id: string, visible: boolean) {
    setSectionVisibility((current) => ({ ...current, [id]: visible }));
    setMessage("");
    setPageError("");
    setFieldErrors({});
  }

  function resetChanges() {
    setValues(initialValues);
    setPageVisible(initialPageVisible);
    setSectionVisibility(initialSectionVisibility);
    setMessage("");
    setPageError("");
    setFieldErrors({});
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!page || saving) return;

    const pageKey = page.key;
    setSaving(true);
    setMessage("");
    setPageError("");
    setFieldErrors({});
    const changedFields = Object.fromEntries(
      Object.entries(values).filter(
        ([id, value]) => initialValues[id] !== value
      )
    );
    const changedSections = Object.fromEntries(
      Object.entries(sectionVisibility).filter(
        ([id, visible]) => initialSectionVisibility[id] !== visible
      )
    );
    const payload: {
      fields?: FieldValues;
      isVisible?: boolean;
      sections?: Record<string, boolean>;
    } = {};
    if (Object.keys(changedFields).length) payload.fields = changedFields;
    if (pageVisible !== initialPageVisible) payload.isVisible = pageVisible;
    if (Object.keys(changedSections).length) payload.sections = changedSections;
    const result = await api.patch<{ page: ContentPage }, ContentErrorData>(
      `/api/admin/content/pages/${encodeURIComponent(pageKey)}`,
      payload
    );
    setSaving(false);

    if (!result.ok || !result.data) {
      setFieldErrors(result.errorData?.fieldErrors ?? {});
      setPageError(result.error ?? "ذخیره محتوای صفحه انجام نشد");
      return;
    }

    const savedPage = result.data.page;
    const savedValues = fieldValues(savedPage.fields);
    const savedSections = sectionValues(savedPage.sections);
    setPage(savedPage);
    setValues(savedValues);
    setInitialValues(savedValues);
    setPageVisible(savedPage.isVisible);
    setInitialPageVisible(savedPage.isVisible);
    setSectionVisibility(savedSections);
    setInitialSectionVisibility(savedSections);
    setPages((current) =>
      current.map((item) =>
        item.key === savedPage.key
          ? {
              key: savedPage.key,
              label: savedPage.label,
              path: savedPage.path,
              isVisible: savedPage.isVisible,
              updatedAt: savedPage.updatedAt,
              updatedBy: savedPage.updatedBy,
            }
          : item
      )
    );
    setMessage("محتوای صفحه ذخیره شد ✅");
    await loadPages();
    router.refresh();
  }

  function reloadSelectedPage() {
    if (!selectedKey || pageLoading) return;
    setPageLoading(true);
    setPageError("");
    setFieldErrors({});
    setMessage("");
    setDetailReload((current) => current + 1);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-bold text-slate-800">📄 محتوای صفحات</h1>
        <p className="mt-1 text-xs leading-6 text-slate-400">
          متن بخش‌های از پیش تعیین‌شده را ویرایش کنید؛ ساختار و چیدمان
          صفحه ثابت می‌ماند.
        </p>
      </div>

      {listError && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3 text-xs text-red-600"
        >
          <span>{listError}</span>
          <button
            type="button"
            onClick={() => {
              const needsInitialSelection = pages.length === 0;
              setListLoading(true);
              setListError("");
              void loadPages(needsInitialSelection);
            }}
            className="font-bold hover:underline"
          >
            تلاش دوباره
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-slate-100 bg-white p-2">
          <h2 className="px-3 py-2 text-xs font-bold text-slate-400">
            صفحات قابل ویرایش
          </h2>
          <div className="space-y-1">
            {listLoading ? (
              <p className="px-3 py-8 text-center text-xs text-slate-400">
                در حال بارگذاری...
              </p>
            ) : pages.length === 0 ? (
              <p className="px-3 py-8 text-center text-xs text-slate-400">
                صفحه‌ای برای ویرایش یافت نشد.
              </p>
            ) : (
              pages.map((item) => {
                const active = item.key === selectedKey;
                return (
                  <button
                    key={item.key}
                    type="button"
                    disabled={saving}
                    onClick={() => selectPage(item.key)}
                    className={`w-full rounded-xl px-3 py-3 text-right transition disabled:cursor-not-allowed disabled:opacity-60 ${
                      active
                        ? "bg-brand-50 text-brand-700 ring-1 ring-brand-100"
                        : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <span className="flex items-center justify-between gap-2 text-sm font-medium">
                      <span>{item.label}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[9px] ${
                          item.isVisible
                            ? "bg-emerald-50 text-emerald-600"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {item.isVisible ? "نمایش" : "مخفی"}
                      </span>
                    </span>
                    <code
                      dir="ltr"
                      className={`mt-1 block truncate text-left text-[10px] ${
                        active ? "text-brand-500" : "text-slate-400"
                      }`}
                    >
                      {item.path}
                    </code>
                    {item.updatedAt && (
                      <span className="mt-1.5 block text-[10px] text-slate-400">
                        ویرایش: {faDateTime(item.updatedAt)}
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <main className="min-w-0">
          {pageLoading ? (
            <div className="grid min-h-[28rem] place-items-center rounded-2xl border border-slate-100 bg-white text-sm text-slate-400">
              در حال بارگذاری محتوا...
            </div>
          ) : pageError && !page ? (
            <div className="grid min-h-[28rem] place-items-center rounded-2xl border border-red-100 bg-white p-6 text-center sm:p-8">
              <div>
                <p className="text-sm text-red-500">{pageError}</p>
                <button
                  type="button"
                  onClick={reloadSelectedPage}
                  className="mt-4 rounded-xl border border-slate-200 px-4 py-2 text-xs text-slate-600 hover:border-brand-300"
                >
                  تلاش دوباره
                </button>
              </div>
            </div>
          ) : page ? (
            <form onSubmit={save} className="space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3 rounded-2xl border border-slate-100 bg-white p-5">
                <div>
                  <h2 className="font-bold text-slate-800">{page.label}</h2>
                  <code
                    dir="ltr"
                    className="mt-1 block text-left text-[11px] text-slate-400"
                  >
                    {page.path}
                  </code>
                </div>
                <div className="text-left text-[11px] leading-6 text-slate-400">
                  {page.updatedAt ? (
                    <>
                      <p>آخرین ویرایش: {faDateTime(page.updatedAt)}</p>
                      {page.updatedBy && <p>ویرایشگر: {page.updatedBy}</p>}
                    </>
                  ) : (
                    <p>هنوز ویرایشی ثبت نشده است.</p>
                  )}
                </div>
              </div>

              <fieldset className="rounded-2xl border border-slate-100 bg-white p-5">
                <legend className="px-2 text-sm font-bold text-slate-700">
                  وضعیت نمایش
                </legend>
                <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl bg-slate-50 px-4 py-3">
                  <span>
                    <span className="block text-sm font-bold text-slate-700">
                      نمایش کامل صفحه
                    </span>
                    <span className="mt-1 block text-[11px] leading-5 text-slate-400">
                      در حالت مخفی، آدرس صفحه پاسخ ۴۰۴ نمایش می‌دهد.
                    </span>
                  </span>
                  <input
                    id="content-field-isVisible"
                    type="checkbox"
                    checked={pageVisible}
                    disabled={saving}
                    aria-invalid={Boolean(fieldErrors.isVisible)}
                    onChange={(event) =>
                      updatePageVisibility(event.target.checked)
                    }
                    className="h-5 w-5 shrink-0 accent-brand-600"
                  />
                </label>
                {fieldErrors.isVisible && (
                  <p className="mt-2 text-[11px] text-red-500">
                    {fieldErrors.isVisible}
                  </p>
                )}

                <div className="mt-5">
                  <h3 className="text-xs font-bold text-slate-500">
                    بخش‌های صفحه
                  </h3>
                  <p className="mt-1 text-[11px] leading-5 text-slate-400">
                    هر بخش را مستقل از سایر بخش‌ها نمایش یا مخفی کنید.
                  </p>
                  <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {page.sections.map((section) => {
                      const errorKey = `sections.${section.id}`;
                      return (
                        <label
                          key={section.id}
                          className="flex cursor-pointer items-center justify-between gap-3 rounded-xl border border-slate-100 px-3 py-3 text-xs text-slate-600"
                        >
                          <span>{section.label}</span>
                          <span className="flex items-center gap-2">
                            <span
                              className={
                                sectionVisibility[section.id]
                                  ? "text-emerald-600"
                                  : "text-slate-400"
                              }
                            >
                              {sectionVisibility[section.id]
                                ? "نمایش"
                                : "مخفی"}
                            </span>
                            <input
                              id={`content-field-${errorKey}`}
                              type="checkbox"
                              checked={sectionVisibility[section.id] ?? true}
                              disabled={saving}
                              aria-invalid={Boolean(fieldErrors[errorKey])}
                              onChange={(event) =>
                                updateSectionVisibility(
                                  section.id,
                                  event.target.checked
                                )
                              }
                              className="h-4 w-4 accent-brand-600"
                            />
                          </span>
                          {fieldErrors[errorKey] && (
                            <span className="sr-only">
                              {fieldErrors[errorKey]}
                            </span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                </div>
              </fieldset>

              {groups.length === 0 ? (
                <div className="rounded-2xl border border-amber-100 bg-amber-50 p-6 text-center sm:p-8 text-sm text-amber-700">
                  برای این صفحه فیلد قابل ویرایشی تعریف نشده است.
                </div>
              ) : (
                groups.map((group) => (
                  <fieldset
                    key={group.label}
                    className="space-y-4 rounded-2xl border border-slate-100 bg-white p-5"
                  >
                    <legend className="px-2 text-sm font-bold text-slate-700">
                      {group.label}
                    </legend>
                    {group.fields.map((field) => {
                      const value = values[field.id] ?? "";
                      const domId = `content-field-${field.id}`;
                      const helpId = `content-field-help-${field.id}`;
                      const errorId = `content-field-error-${field.id}`;
                      const fieldError = fieldErrors[field.id];
                      const control = safeControl(field.control);
                      const commonProps = {
                        id: domId,
                        name: field.id,
                        required: field.required,
                        maxLength: field.maxLength,
                        dir: inputDirection(field),
                        disabled: saving,
                        value,
                        "aria-invalid": Boolean(fieldError),
                        "aria-describedby": fieldError
                          ? errorId
                          : field.help
                            ? helpId
                            : undefined,
                        onChange: (
                          event: React.ChangeEvent<
                            HTMLInputElement | HTMLTextAreaElement
                          >
                        ) => updateField(field.id, event.target.value),
                      };

                      return (
                        <div key={field.id}>
                          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
                            <label
                              htmlFor={domId}
                              className="text-xs font-medium text-slate-600"
                            >
                              {field.label}
                              {field.required && (
                                <span className="mr-1 text-red-400">*</span>
                              )}
                            </label>
                            {field.maxLength > 0 && (
                              <span className="text-[10px] text-slate-400 font-num">
                                {value.length.toLocaleString("fa-IR")} /{" "}
                                {field.maxLength.toLocaleString("fa-IR")}
                              </span>
                            )}
                          </div>
                          {control === "textarea" ? (
                            <textarea
                              {...commonProps}
                              rows={field.rows ?? 4}
                              className={`${INPUT_CLASS} resize-y leading-7`}
                            />
                          ) : (
                            <input
                              {...commonProps}
                              type={control}
                              className={INPUT_CLASS}
                            />
                          )}
                          {field.help && (
                            <p
                              id={helpId}
                              className="mt-1.5 text-[11px] leading-5 text-slate-400"
                            >
                              {field.help}
                            </p>
                          )}
                          {fieldError && (
                            <p
                              id={errorId}
                              className="mt-1.5 text-[11px] leading-5 text-red-500"
                            >
                              {fieldError}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </fieldset>
                ))
              )}

              {pageError && (
                <p
                  role="alert"
                  className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-500"
                >
                  {pageError}
                </p>
              )}
              {message && (
                <p
                  role="status"
                  className="rounded-xl bg-emerald-50 px-4 py-3 text-xs text-emerald-700"
                >
                  {message}
                </p>
              )}

              <div className="sticky bottom-3 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-100 bg-white/95 p-4 shadow-[0_12px_40px_-25px_rgba(20,36,79,0.5)] backdrop-blur">
                <button
                  disabled={saving || groups.length === 0 || !dirty}
                  className="rounded-xl bg-brand-600 px-7 py-2.5 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {saving ? "در حال ذخیره..." : "ذخیره تغییرات"}
                </button>
                <button
                  type="button"
                  disabled={saving || !dirty}
                  onClick={resetChanges}
                  className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm text-slate-600 transition hover:border-brand-300 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  لغو تغییرات
                </button>
                {dirty && (
                  <span className="text-xs text-amber-600">
                    تغییرات ذخیره نشده است.
                  </span>
                )}
              </div>
            </form>
          ) : (
            <div className="grid min-h-[28rem] place-items-center rounded-2xl border border-slate-100 bg-white p-6 text-center sm:p-8 text-sm text-slate-400">
              یک صفحه را برای ویرایش انتخاب کنید.
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
