"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatPrice } from "@/lib/products";
import { api } from "@/lib/client-api";

type CartItem = {
  id: number;
  qty: number;
  product: {
    id: number;
    title: string;
    emoji: string;
    image?: string | null;
    price: number;
    oldPrice?: number;
    stock?: number;
  };
};

type Cart = {
  items: CartItem[];
  itemsCount: number;
  itemsPrice: number;
  discount: number;
  totalPrice: number;
};

type CheckoutInfo = {
  fullName: string;
  province: string;
  city: string;
  address: string;
  postalCode: string;
};

type SavedAddress = {
  id: number;
  title: string;
  fullName: string;
  province: string;
  city: string;
  address: string;
  isDefault: boolean;
};

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyItem, setBusyItem] = useState<number | null>(null);
  const [checkout, setCheckout] = useState(false);
  const [info, setInfo] = useState<CheckoutInfo>({
    fullName: "",
    province: "",
    city: "",
    address: "",
    postalCode: "",
  });
  const [addresses, setAddresses] = useState<SavedAddress[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [orderCode, setOrderCode] = useState<string | null>(null);

  async function loadCart() {
    try {
      const res = await fetch("/api/cart");
      const json = await res.json();
      if (json.ok) setCart(json.data.cart);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCart();
    // آدرس‌های ذخیره‌شده کاربر (اگر لاگین باشد)
    api
      .get<{ addresses: SavedAddress[] }>("/api/auth/addresses")
      .then((res) => {
        if (res.ok && res.data) {
          setAddresses(res.data.addresses);
          const def =
            res.data.addresses.find((a) => a.isDefault) ??
            res.data.addresses[0];
          if (def) setSelectedAddress(def.id);
        }
      });
  }, []);

  function notifyHeader() {
    window.dispatchEvent(new CustomEvent("cart:updated"));
  }

  async function changeQty(item: CartItem, qty: number) {
    if (qty < 1) return;
    setBusyItem(item.id);
    setError("");
    const res = await api.patch<{ cart: Cart }>(`/api/cart/items/${item.id}`, {
      qty,
    });
    setBusyItem(null);
    if (res.ok && res.data) {
      setCart(res.data.cart);
      notifyHeader();
    } else {
      setError(res.error ?? "خطا در تغییر تعداد");
    }
  }

  async function removeItem(item: CartItem) {
    setBusyItem(item.id);
    setError("");
    const res = await api.delete<{ cart: Cart }>(`/api/cart/items/${item.id}`);
    setBusyItem(null);
    if (res.ok && res.data) {
      setCart(res.data.cart);
      notifyHeader();
    }
  }

  async function submitOrder(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    // اگر آدرس ذخیره‌شده انتخاب شده، فقط شناسه‌اش ارسال می‌شود
    const payload =
      addresses.length > 0 && selectedAddress
        ? { addressId: selectedAddress }
        : info;
    const res = await api.post<{ order: { code: string } }>(
      "/api/orders",
      payload
    );
    setSubmitting(false);
    if (!res.ok || !res.data) {
      if (res.status === 401) {
        setError("برای ثبت سفارش ابتدا وارد حساب خود شوید");
      } else {
        setError(res.error ?? "خطا در ثبت سفارش");
      }
      return;
    }
    setOrderCode(res.data.order.code);
    setCart(null);
    notifyHeader();
    loadCart();
  }

  // ─── حالت‌های صفحه ───────────────────────────────────────

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 text-center text-sm text-slate-400">
        در حال بارگذاری سبد خرید...
      </div>
    );
  }

  if (orderCode) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <div className="rounded-3xl border border-brand-100 bg-brand-50 p-8">
          <span className="mb-4 block text-5xl">🎉</span>
          <h1 className="mb-2 text-lg font-bold text-slate-800">
            سفارش شما با موفقیت ثبت شد
          </h1>
          <p className="mb-6 text-sm text-slate-500">
            کد پیگیری سفارش:{" "}
            <b className="font-num text-brand-700" dir="ltr">
              {orderCode}
            </b>
          </p>
          <div className="flex justify-center gap-3 text-sm">
            <Link
              href="/orders"
              className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white transition hover:bg-brand-700"
            >
              مشاهده سفارش‌ها
            </Link>
            <Link
              href="/"
              className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 font-medium text-slate-600"
            >
              بازگشت به فروشگاه
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!cart || cart.items.length === 0) {
    return (
      <div className="mx-auto max-w-md px-4 py-16 text-center">
        <span className="mb-4 block text-5xl">🛒</span>
        <h1 className="mb-2 text-lg font-bold text-slate-800">
          سبد خرید شما خالی است
        </h1>
        <p className="mb-6 text-sm text-slate-500">
          می‌توانید از میان محصولات فروشگاه، کالای موردنظرتان را انتخاب کنید.
        </p>
        <Link
          href="/"
          className="inline-block rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          مشاهده محصولات
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      <h1 className="mb-5 text-lg font-bold text-slate-800">
        سبد خرید{" "}
        <span className="text-sm font-normal text-slate-400 font-num">
          ({cart.itemsCount.toLocaleString("fa-IR")} کالا)
        </span>
      </h1>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* اقلام */}
        <div className="flex-1 space-y-3">
          {cart.items.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-4"
            >
              <Link
                href={`/product/${item.product.id}`}
                className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-xl bg-slate-50 text-4xl"
              >
                {item.product.image ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.product.image}
                    alt={item.product.title}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  item.product.emoji
                )}
              </Link>
              <div className="min-w-0 flex-1">
                <Link
                  href={`/product/${item.product.id}`}
                  className="mb-2 block truncate text-sm font-medium text-slate-700 hover:text-brand-700"
                >
                  {item.product.title}
                </Link>
                <div className="flex items-baseline gap-1 text-sm">
                  <span className="font-bold text-slate-800 font-num">
                    {formatPrice(item.product.price * item.qty)}
                  </span>
                  <span className="text-xs text-slate-400">تومان</span>
                  {item.product.oldPrice && (
                    <span className="mr-2 text-xs text-slate-300 line-through font-num">
                      {formatPrice(item.product.oldPrice * item.qty)}
                    </span>
                  )}
                </div>
              </div>

              {/* کنترل تعداد */}
              <div className="flex items-center gap-2 rounded-xl border border-slate-200 px-2 py-1.5">
                <button
                  disabled={busyItem === item.id}
                  onClick={() => changeQty(item, item.qty + 1)}
                  className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-brand-600 hover:bg-slate-200 disabled:opacity-50"
                >
                  +
                </button>
                <span className="w-6 text-center text-sm font-num">
                  {item.qty.toLocaleString("fa-IR")}
                </span>
                {item.qty > 1 ? (
                  <button
                    disabled={busyItem === item.id}
                    onClick={() => changeQty(item, item.qty - 1)}
                    className="grid h-7 w-7 place-items-center rounded-lg bg-slate-100 text-slate-500 hover:bg-slate-200 disabled:opacity-50"
                  >
                    −
                  </button>
                ) : (
                  <button
                    disabled={busyItem === item.id}
                    onClick={() => removeItem(item)}
                    className="grid h-7 w-7 place-items-center rounded-lg bg-red-50 text-red-500 hover:bg-red-100 disabled:opacity-50"
                    title="حذف از سبد"
                  >
                    🗑
                  </button>
                )}
              </div>
            </div>
          ))}

          {error && !checkout && (
            <p className="text-xs text-red-500">{error}</p>
          )}
        </div>

        {/* خلاصه و ثبت سفارش */}
        <div className="lg:w-80 lg:shrink-0">
          <div className="rounded-2xl border border-slate-100 bg-white p-5 lg:sticky lg:top-28">
            <div className="space-y-3 border-b border-slate-100 pb-4 text-sm">
              <div className="flex justify-between text-slate-500">
                <span>
                  قیمت کالاها{" "}
                  <span className="font-num">
                    ({cart.itemsCount.toLocaleString("fa-IR")})
                  </span>
                </span>
                <span className="font-num">
                  {formatPrice(cart.itemsPrice)} تومان
                </span>
              </div>
              {cart.discount > 0 && (
                <div className="flex justify-between text-red-500">
                  <span>سود شما از خرید</span>
                  <span className="font-num">
                    {formatPrice(cart.discount)} تومان
                  </span>
                </div>
              )}
              <div className="flex justify-between font-bold text-slate-800">
                <span>مبلغ قابل پرداخت</span>
                <span className="font-num">
                  {formatPrice(cart.totalPrice)} تومان
                </span>
              </div>
            </div>

            {!checkout ? (
              <button
                onClick={() => setCheckout(true)}
                className="mt-4 w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700"
              >
                ادامه فرایند خرید
              </button>
            ) : (
              <form onSubmit={submitOrder} className="mt-4 space-y-3">
                {addresses.length > 0 ? (
                  /* انتخاب از دفترچه آدرس */
                  <>
                    <p className="text-xs font-medium text-slate-600">
                      آدرس تحویل را انتخاب کنید:
                    </p>
                    {addresses.map((a) => (
                      <label
                        key={a.id}
                        className={`flex cursor-pointer gap-2 rounded-xl border p-3 text-xs transition ${
                          selectedAddress === a.id
                            ? "border-brand-400 bg-brand-50/50"
                            : "border-slate-200 hover:border-slate-300"
                        }`}
                      >
                        <input
                          type="radio"
                          name="address"
                          checked={selectedAddress === a.id}
                          onChange={() => setSelectedAddress(a.id)}
                          className="mt-0.5 h-4 w-4 shrink-0 accent-brand-600"
                        />
                        <span className="min-w-0">
                          <span className="block font-medium text-slate-700">
                            {a.title} — {a.fullName}
                          </span>
                          <span className="mt-0.5 block leading-5 text-slate-500">
                            {a.province}، {a.city}، {a.address}
                          </span>
                        </span>
                      </label>
                    ))}
                    <Link
                      href="/profile/addresses"
                      className="block text-center text-xs text-brand-600 hover:underline"
                    >
                      + افزودن آدرس جدید
                    </Link>
                  </>
                ) : (
                  /* فرم دستی برای کاربری که آدرس ذخیره‌شده ندارد */
                  <>
                    <input
                      required
                      placeholder="نام و نام خانوادگی تحویل‌گیرنده"
                      value={info.fullName}
                      onChange={(e) =>
                        setInfo({ ...info, fullName: e.target.value })
                      }
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-brand-400 focus:bg-white"
                    />
                    <div className="flex gap-2">
                      <input
                        required
                        placeholder="استان"
                        value={info.province}
                        onChange={(e) =>
                          setInfo({ ...info, province: e.target.value })
                        }
                        className="w-1/2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-brand-400 focus:bg-white"
                      />
                      <input
                        required
                        placeholder="شهر"
                        value={info.city}
                        onChange={(e) =>
                          setInfo({ ...info, city: e.target.value })
                        }
                        className="w-1/2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-brand-400 focus:bg-white"
                      />
                    </div>
                    <textarea
                      required
                      placeholder="آدرس کامل پستی"
                      rows={3}
                      value={info.address}
                      onChange={(e) =>
                        setInfo({ ...info, address: e.target.value })
                      }
                      className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-brand-400 focus:bg-white"
                    />
                    <input
                      placeholder="کد پستی (اختیاری)"
                      dir="ltr"
                      value={info.postalCode}
                      onChange={(e) =>
                        setInfo({ ...info, postalCode: e.target.value })
                      }
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-center text-sm font-num outline-none focus:border-brand-400 focus:bg-white"
                    />
                  </>
                )}

                {error && <p className="text-xs text-red-500">{error}</p>}
                {error.includes("وارد") && (
                  <Link
                    href="/login?next=%2Fcart"
                    className="block text-center text-xs text-brand-600 hover:underline"
                  >
                    ورود به حساب کاربری ←
                  </Link>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
                >
                  {submitting ? "در حال ثبت سفارش..." : "ثبت نهایی سفارش"}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
