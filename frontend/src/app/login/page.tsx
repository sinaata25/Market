"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toEnglishDigits, isValidIranMobile } from "@/lib/utils";
import { api } from "@/lib/client-api";

type Step = "phone" | "otp";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [otp, setOtp] = useState<string[]>(["", "", "", "", ""]);
  const [seconds, setSeconds] = useState(0);
  const [devCode, setDevCode] = useState<string | null>(null);
  const otpRefs = useRef<Array<HTMLInputElement | null>>([]);

  // شمارش معکوس ارسال مجدد کد
  useEffect(() => {
    if (seconds <= 0) return;
    const t = setInterval(() => setSeconds((s) => s - 1), 1000);
    return () => clearInterval(t);
  }, [seconds]);

  // درخواست ارسال کد از سرور
  async function sendOtp(): Promise<boolean> {
    setLoading(true);
    setError("");
    const res = await api.post<{ ttl?: number; devCode?: string }>(
      "/api/auth/otp/send",
      { phone }
    );
    setLoading(false);
    if (!res.ok) {
      setError(res.error ?? "خطا در ارسال کد");
      return false;
    }
    setSeconds(res.data?.ttl ?? 120);
    // تا زمان اتصال سرویس پیامک، کد برای تست نمایش داده می‌شود
    setDevCode(res.data?.devCode ?? null);
    return true;
  }

  async function submitPhone(e: React.FormEvent) {
    e.preventDefault();
    if (!isValidIranMobile(phone)) {
      setError("شماره موبایل را به‌درستی وارد کنید (مثال: ۰۹۱۲۱۲۳۴۵۶۷)");
      return;
    }
    const sent = await sendOtp();
    if (sent) {
      setStep("otp");
      setOtp(["", "", "", "", ""]);
      setTimeout(() => otpRefs.current[0]?.focus(), 50);
    }
  }

  function handleOtpChange(index: number, value: string) {
    const digit = toEnglishDigits(value).replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);
    if (digit && index < 4) otpRefs.current[index + 1]?.focus();
  }

  function handleOtpKeyDown(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  }

  async function submitOtp(e: React.FormEvent) {
    e.preventDefault();
    if (otp.some((d) => d === "")) {
      setError("کد ۵ رقمی را کامل وارد کنید");
      return;
    }
    setLoading(true);
    setError("");
    const res = await api.post("/api/auth/otp/verify", {
      phone,
      code: otp.join(""),
    });
    setLoading(false);
    if (!res.ok) {
      setError(res.error ?? "خطا در ورود");
      return;
    }
    // ورود موفق → صفحه اصلی
    window.dispatchEvent(new CustomEvent("cart:updated"));
    router.push("/");
    router.refresh();
  }

  return (
    <div className="flex min-h-[calc(100vh-200px)] items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-3xl border border-slate-100 bg-white p-6 shadow-sm sm:p-8">
        {/* لوگو */}
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-brand-600 text-2xl">
            🌾
          </span>
          <h1 className="text-xl font-bold text-slate-800">
            ورود | ثبت‌نام
          </h1>
          <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-500">
            {step === "phone"
              ? "سلام!\nبرای ورود یا ثبت‌نام شماره موبایل خود را وارد کنید."
              : `کد تأیید برای شماره ${phone} پیامک شد.`}
          </p>
        </div>

        {/* مرحله شماره موبایل */}
        {step === "phone" && (
          <form onSubmit={submitPhone} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-600">
                شماره موبایل
              </label>
              <input
                type="tel"
                inputMode="numeric"
                dir="ltr"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="09xxxxxxxxx"
                autoFocus
                className={`w-full rounded-xl border bg-slate-50 px-4 py-3 text-center font-num tracking-widest outline-none transition focus:bg-white ${
                  error
                    ? "border-red-300 focus:border-red-400"
                    : "border-slate-200 focus:border-brand-400"
                }`}
              />
            </div>

            {error && <p className="text-xs text-red-500">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {loading ? "در حال ارسال کد..." : "ورود"}
            </button>

            <p className="text-center text-xs leading-6 text-slate-400">
              ورود شما به معنای پذیرش{" "}
              <Link href="#" className="text-brand-600 hover:underline">
                شرایط و قوانین
              </Link>{" "}
              و{" "}
              <Link href="#" className="text-brand-600 hover:underline">
                حریم خصوصی
              </Link>{" "}
              است.
            </p>
          </form>
        )}

        {/* مرحله کد تأیید */}
        {step === "otp" && (
          <form onSubmit={submitOtp} className="space-y-5">
            {/* تا اتصال سرویس پیامک، کد برای تست اینجا نمایش داده می‌شود */}
            {devCode && (
              <p className="rounded-xl bg-amber-50 px-4 py-2.5 text-center text-xs text-amber-700">
                کد تست (سرویس پیامک هنوز متصل نیست):{" "}
                <b className="font-num" dir="ltr">
                  {devCode}
                </b>
              </p>
            )}

            <div dir="ltr" className="flex justify-center gap-2">
              {otp.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => {
                    otpRefs.current[i] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={d}
                  onChange={(e) => handleOtpChange(i, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(i, e)}
                  className={`h-12 w-11 rounded-xl border bg-slate-50 text-center text-lg font-bold font-num outline-none transition focus:bg-white ${
                    error
                      ? "border-red-300 focus:border-red-400"
                      : "border-slate-200 focus:border-brand-400"
                  }`}
                />
              ))}
            </div>

            {error && <p className="text-center text-xs text-red-500">{error}</p>}

            <div className="text-center text-xs text-slate-500">
              {seconds > 0 ? (
                <span className="font-num">
                  ارسال مجدد کد تا {Math.floor(seconds / 60)}:
                  {String(seconds % 60).padStart(2, "0")}
                </span>
              ) : (
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => sendOtp()}
                  className="text-brand-600 hover:underline disabled:opacity-60"
                >
                  ارسال مجدد کد تأیید
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {loading ? "در حال بررسی..." : "تأیید و ورود"}
            </button>

            <button
              type="button"
              onClick={() => {
                setStep("phone");
                setOtp(["", "", "", "", ""]);
                setError("");
                setDevCode(null);
              }}
              className="w-full text-center text-xs text-slate-400 hover:text-slate-600"
            >
              ← ویرایش شماره موبایل
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
