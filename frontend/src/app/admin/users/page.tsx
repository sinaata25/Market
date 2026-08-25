"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/client-api";
import { faNum, Pager, EmptyRow } from "@/components/admin/ui";

type User = {
  id: number;
  phone: string;
  name: string | null;
  isStaff: boolean;
  isManagerAdmin: boolean;
  isSeoManager: boolean;
  isSuperuser: boolean;
  isActive: boolean;
  dateJoined: string;
  ordersCount: number;
};

// این فهرست فقط خواندنی است؛ تغییر نقش‌ها فقط از مسیرهای مخصوص سوپریوزر
// انجام می‌شود، پس اینجا هیچ کنترل ارتقای نقشی وجود ندارد.
function roleBadge(user: User): { label: string; className: string } {
  if (user.isSuperuser)
    return { label: "مدیر سیستم", className: "bg-rose-50 text-rose-600" };
  if (user.isManagerAdmin)
    return { label: "مدیر اجرایی", className: "bg-violet-50 text-violet-600" };
  if (user.isSeoManager)
    return { label: "مدیر سئو", className: "bg-amber-50 text-amber-600" };
  if (user.isStaff)
    return { label: "کارمند", className: "bg-blue-50 text-blue-600" };
  return { label: "مشتری", className: "bg-slate-100 text-slate-500" };
}

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    const qs = new URLSearchParams({ page: String(page) });
    if (search.trim()) qs.set("search", search.trim());
    api
      .get<{ users: User[]; pages: number; total: number }>(
        `/api/admin/users?${qs}`
      )
      .then((res) => {
        if (res.ok && res.data) {
          setUsers(res.data.users);
          setPages(res.data.pages);
          setTotal(res.data.total);
        }
        setLoading(false);
      });
  }, [page, search]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-bold text-slate-800">
          کاربران{" "}
          <span className="text-sm font-normal text-slate-400 font-num">
            ({faNum(total)})
          </span>
        </h1>
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="جستجو: شماره یا نام..."
          className="w-full rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs outline-none focus:border-brand-400 sm:w-56"
        />
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-100 bg-white">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-right text-[11px] text-slate-400">
              <th className="px-5 py-3 font-medium">کاربر</th>
              <th className="px-3 py-3 font-medium">شماره موبایل</th>
              <th className="px-3 py-3 font-medium">تاریخ عضویت</th>
              <th className="px-3 py-3 font-medium">سفارش‌ها</th>
              <th className="px-5 py-3 font-medium">نقش</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <EmptyRow colSpan={5} text="در حال بارگذاری..." />
            ) : users.length === 0 ? (
              <EmptyRow colSpan={5} text="کاربری یافت نشد" />
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
                  <td className="px-5 py-3">
                    <span
                      className={`rounded-lg px-2.5 py-1 text-[11px] font-medium ${roleBadge(u).className}`}
                    >
                      {roleBadge(u).label}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pager page={page} pages={pages} onPage={setPage} />
    </div>
  );
}
