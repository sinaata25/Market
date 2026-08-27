"use client";

// مدیریت کاربران — دامنه‌ی هر نقش را بک‌اند تعیین می‌کند
//
// این صفحه هیچ قاعده‌ی دسترسی‌ای از خودش ندارد: فهرست فقط شامل کاربرانی است که
// بک‌اند اجازه‌ی دیدنشان را داده (`accounts/selectors.py`)، و دکمه‌ها از روی
// `permissions` همان پاسخ ساخته می‌شوند. یعنی اگر مدیر عادی دکمه‌ی حذف را
// نمی‌بیند، به این دلیل نیست که اینجا پنهانش کرده‌ایم؛ بک‌اند گفته مجاز نیست
// و همان درخواست را هم رد می‌کند.

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/client-api";
import { faNum, Pager, EmptyRow } from "@/components/admin/ui";
import { useDebouncedValue } from "@/components/admin/useDebouncedValue";
import { ROLE_BADGES, ROLE_LABELS, type Role } from "@/lib/admin-roles";

type User = {
  id: number;
  phone: string;
  name: string | null;
  role: Role;
  roleLabel: string;
  isActive: boolean;
  canAccessSeo: boolean;
  dateJoined: string;
  ordersCount: number;
};

type ListPermissions = {
  creatableRoles: Role[];
  visibleRoles: Role[];
  canViewAdmins: boolean;
  canGrantSeoAccess: boolean;
};

type RowPermissions = {
  canEdit: boolean;
  canChangeRole: boolean;
  canChangeState: boolean;
  canDelete: boolean;
  canGrantSeoAccess: boolean;
};

const NO_PERMISSIONS: ListPermissions = {
  creatableRoles: [],
  visibleRoles: [],
  canViewAdmins: false,
  canGrantSeoAccess: false,
};

type Draft = { phone: string; name: string; role: Role; canAccessSeo: boolean };

const EMPTY_DRAFT: Draft = {
  phone: "",
  name: "",
  role: "customer",
  canAccessSeo: false,
};

function RoleBadge({ role }: { role: Role }) {
  return (
    <span
      className={`rounded-lg px-2.5 py-1 text-[11px] font-medium ${ROLE_BADGES[role]}`}
    >
      {ROLE_LABELS[role]}
    </span>
  );
}

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [permissions, setPermissions] =
    useState<ListPermissions>(NO_PERMISSIONS);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "">("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [editing, setEditing] = useState<User | null>(null);
  const [editingRights, setEditingRights] = useState<RowPermissions | null>(
    null
  );
  const requestId = useRef(0);
  const debouncedSearch = useDebouncedValue(search);

  const load = useCallback(async () => {
    if (search !== debouncedSearch) return;
    const currentRequest = ++requestId.current;
    await Promise.resolve();
    if (currentRequest !== requestId.current) return;
    setLoading(true);
    setLoadError("");
    const qs = new URLSearchParams({ page: String(page) });
    if (debouncedSearch.trim()) qs.set("search", debouncedSearch.trim());
    if (roleFilter) qs.set("role", roleFilter);
    const res = await api.get<{
      users: User[];
      pages: number;
      total: number;
      permissions: ListPermissions;
    }>(`/api/admin/users?${qs}`);
    if (currentRequest !== requestId.current) return;
    if (res.ok && res.data) {
      setUsers(res.data.users);
      setPages(res.data.pages);
      setTotal(res.data.total);
      setPermissions(res.data.permissions);
    } else {
      setUsers([]);
      setPermissions(NO_PERMISSIONS);
      setLoadError(res.error ?? "دریافت کاربران انجام نشد");
    }
    setLoading(false);
  }, [page, search, debouncedSearch, roleFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  function flash(message: string) {
    setNotice(message);
    setFormError("");
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    const res = await api.post<{ user: User }>("/api/admin/users", {
      phone: draft.phone.trim(),
      name: draft.name.trim(),
      role: draft.role,
      ...(draft.role === "manager_admin" && permissions.canGrantSeoAccess
        ? { canAccessSeo: draft.canAccessSeo }
        : {}),
    });
    setSaving(false);
    if (!res.ok) {
      setFormError(res.error ?? "ساخت کاربر ناموفق بود");
      return;
    }
    setDraft(EMPTY_DRAFT);
    setCreating(false);
    flash("کاربر ساخته شد");
    void load();
  }

  async function openEditor(user: User) {
    setFormError("");
    setNotice("");
    const res = await api.get<{ user: User; permissions: RowPermissions }>(
      `/api/admin/users/${user.id}`
    );
    if (!res.ok || !res.data) {
      setLoadError(res.error ?? "دریافت اطلاعات کاربر انجام نشد");
      return;
    }
    setEditing(res.data.user);
    setEditingRights(res.data.permissions);
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editing || !editingRights) return;
    setSaving(true);
    // فقط فیلدهایی فرستاده می‌شوند که این کاربر اجازه‌ی تغییرشان را دارد
    const payload: Record<string, unknown> = {};
    if (editingRights.canEdit) {
      payload.phone = editing.phone.trim();
      payload.name = editing.name?.trim() ?? "";
    }
    if (editingRights.canChangeRole) payload.role = editing.role;
    if (editingRights.canChangeState) payload.isActive = editing.isActive;
    if (editingRights.canGrantSeoAccess && editing.role === "manager_admin") {
      payload.canAccessSeo = editing.canAccessSeo;
    }

    const res = await api.patch<{ user: User }>(
      `/api/admin/users/${editing.id}`,
      payload
    );
    setSaving(false);
    if (!res.ok) {
      setFormError(res.error ?? "ویرایش ناموفق بود");
      return;
    }
    setEditing(null);
    setEditingRights(null);
    flash("اطلاعات حساب به‌روزرسانی شد");
    void load();
  }

  async function remove(user: User) {
    setSaving(true);
    const res = await api.delete(`/api/admin/users/${user.id}`);
    setSaving(false);
    if (!res.ok) {
      setFormError(res.error ?? "حذف ناموفق بود");
      return;
    }
    setEditing(null);
    setEditingRights(null);
    flash("حساب حذف شد");
    void load();
  }

  const canCreate = permissions.creatableRoles.length > 0;
  const filterableRoles = permissions.visibleRoles;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          {permissions.canViewAdmins ? "کاربران" : "مشتریان"}{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(total)})
          </span>
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          {filterableRoles.length > 1 && (
            <select
              value={roleFilter}
              onChange={(e) => {
                requestId.current += 1;
                setLoading(true);
                setRoleFilter(e.target.value as Role | "");
                setPage(1);
              }}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs outline-none focus:border-brand-400"
            >
              <option value="">همه‌ی نقش‌ها</option>
              {filterableRoles.map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role]}
                </option>
              ))}
            </select>
          )}
          <input
            type="search"
            maxLength={200}
            value={search}
            onChange={(e) => {
              requestId.current += 1;
              setLoading(true);
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="جستجو: شماره یا نام..."
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400 sm:w-56"
          />
          {canCreate && (
            <button
              onClick={() => {
                setCreating((open) => !open);
                setFormError("");
                setNotice("");
              }}
              className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-brand-700"
            >
              {creating ? "بستن" : "+ کاربر جدید"}
            </button>
          )}
        </div>
      </div>

      {notice && (
        <p className="rounded-xl bg-emerald-50 px-4 py-2.5 text-xs text-emerald-700">
          {notice}
        </p>
      )}
      {formError && (
        <p className="rounded-xl bg-red-50 px-4 py-2.5 text-xs text-red-600">
          {formError}
        </p>
      )}

      {creating && canCreate && (
        <form
          onSubmit={create}
          className="grid gap-3 rounded-2xl border border-slate-100 bg-white p-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          <input
            required
            value={draft.phone}
            onChange={(e) => setDraft({ ...draft, phone: e.target.value })}
            placeholder="شماره موبایل"
            dir="ltr"
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs outline-none focus:border-brand-400 font-num"
          />
          <input
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="نام (اختیاری)"
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs outline-none focus:border-brand-400"
          />
          <select
            value={draft.role}
            onChange={(e) =>
              setDraft({ ...draft, role: e.target.value as Role })
            }
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs outline-none focus:border-brand-400"
          >
            {/* فقط نقش‌هایی که بک‌اند اجازه‌ی ساختشان را داده است */}
            {permissions.creatableRoles.map((role) => (
              <option key={role} value={role}>
                {ROLE_LABELS[role]}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-3">
            {draft.role === "manager_admin" && permissions.canGrantSeoAccess && (
              <label className="flex items-center gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={draft.canAccessSeo}
                  onChange={(e) =>
                    setDraft({ ...draft, canAccessSeo: e.target.checked })
                  }
                />
                دسترسی سئو
              </label>
            )}
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white disabled:opacity-50"
            >
              ساخت
            </button>
          </div>
        </form>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">کاربر</th>
              <th className="px-3 py-3 font-medium">شماره موبایل</th>
              <th className="px-3 py-3 font-medium">تاریخ عضویت</th>
              <th className="px-3 py-3 font-medium">سفارش‌ها</th>
              <th className="px-3 py-3 font-medium">نقش</th>
              <th className="px-3 py-3 font-medium">وضعیت</th>
              <th className="px-5 py-3 font-medium"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={7} text="در حال بارگذاری..." />
            ) : loadError ? (
              <EmptyRow colSpan={7} text={loadError} />
            ) : users.length === 0 ? (
              <EmptyRow colSpan={7} text="کاربری یافت نشد" />
            ) : (
              users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/60">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-50 text-sm">
                        👤
                      </span>
                      <span className="text-xs text-slate-700">
                        {u.name ?? "—"}
                      </span>
                    </div>
                  </td>
                  <td
                    className="px-3 py-3 text-xs text-slate-500 font-num"
                    dir="ltr"
                  >
                    {u.phone}
                  </td>
                  <td className="px-3 py-3 text-[11px] text-slate-400 font-num">
                    {new Date(u.dateJoined).toLocaleDateString("fa-IR")}
                  </td>
                  <td className="px-3 py-3 text-xs text-slate-600 font-num">
                    {faNum(u.ordersCount)}
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center gap-1.5">
                      <RoleBadge role={u.role} />
                      {u.canAccessSeo && (
                        <span
                          title="دسترسی پنل سئو"
                          className="rounded-lg bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-600"
                        >
                          سئو
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`rounded-lg px-2.5 py-1 text-[11px] font-medium ${
                        u.isActive
                          ? "bg-emerald-50 text-emerald-600"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {u.isActive ? "فعال" : "غیرفعال"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-left">
                    <button
                      onClick={() => void openEditor(u)}
                      className="rounded-lg px-3 py-1.5 text-[11px] text-brand-600 transition hover:bg-brand-50"
                    >
                      مدیریت
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pager
        page={page}
        pages={pages}
        onPage={(nextPage) => {
          requestId.current += 1;
          setLoading(true);
          setPage(nextPage);
        }}
      />

      {editing && editingRights && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4">
          <form
            onSubmit={saveEdit}
            className="w-full max-w-md space-y-3 rounded-2xl bg-white p-5"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800">
                مدیریت حساب
              </h2>
              <RoleBadge role={editing.role} />
            </div>

            {/* هر فیلد فقط وقتی رندر می‌شود که بک‌اند اجازه‌اش را داده باشد */}
            <label className="block text-xs text-slate-500">
              نام
              <input
                disabled={!editingRights.canEdit}
                value={editing.name ?? ""}
                onChange={(e) =>
                  setEditing({ ...editing, name: e.target.value })
                }
                className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-xs text-slate-700 outline-none focus:border-brand-400 disabled:bg-slate-50"
              />
            </label>

            <label className="block text-xs text-slate-500">
              شماره موبایل
              <input
                disabled={!editingRights.canEdit}
                dir="ltr"
                value={editing.phone}
                onChange={(e) =>
                  setEditing({ ...editing, phone: e.target.value })
                }
                className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-xs text-slate-700 outline-none focus:border-brand-400 font-num disabled:bg-slate-50"
              />
            </label>

            {editingRights.canChangeRole && (
              <label className="block text-xs text-slate-500">
                نقش
                <select
                  value={editing.role}
                  onChange={(e) =>
                    setEditing({ ...editing, role: e.target.value as Role })
                  }
                  className="mt-1 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-xs text-slate-700 outline-none focus:border-brand-400"
                >
                  {/* نقش فعلی همیشه هست تا فرم بدون تغییر هم معتبر بماند */}
                  {Array.from(
                    new Set<Role>([editing.role, ...permissions.creatableRoles])
                  ).map((role) => (
                    <option key={role} value={role}>
                      {ROLE_LABELS[role]}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {editingRights.canGrantSeoAccess &&
              editing.role === "manager_admin" && (
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    checked={editing.canAccessSeo}
                    onChange={(e) =>
                      setEditing({
                        ...editing,
                        canAccessSeo: e.target.checked,
                      })
                    }
                  />
                  دسترسی پنل سئو
                </label>
              )}

            {editingRights.canChangeState && (
              <label className="flex items-center gap-2 text-xs text-slate-600">
                <input
                  type="checkbox"
                  checked={editing.isActive}
                  onChange={(e) =>
                    setEditing({ ...editing, isActive: e.target.checked })
                  }
                />
                حساب فعال است
              </label>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
              {editingRights.canDelete ? (
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => void remove(editing)}
                  className="rounded-xl px-4 py-2.5 text-xs font-bold text-red-500 transition hover:bg-red-50 disabled:opacity-50"
                >
                  حذف حساب
                </button>
              ) : (
                <span />
              )}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEditing(null);
                    setEditingRights(null);
                  }}
                  className="rounded-xl px-4 py-2.5 text-xs text-slate-500 transition hover:bg-slate-50"
                >
                  انصراف
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-bold text-white disabled:opacity-50"
                >
                  ذخیره
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
