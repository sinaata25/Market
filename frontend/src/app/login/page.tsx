"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  isValidIranMobile,
  normalizeIranMobile,
  safeNextPath,
  toEnglishDigits,
} from "@/lib/utils";
import {
  api,
  notifyAuthChanged,
  subscribeAuthChanged,
} from "@/lib/client-api";

const DEFAULT_OTP_LENGTH = 4;
const MIN_OTP_LENGTH = 4;
const MAX_OTP_LENGTH = 10;
const FALLBACK_EXPIRES_IN = 120;
const FALLBACK_RESEND_AFTER = 60;
const OTP_STORAGE_KEY = "market:otp-ui:v2";
const OTP_STORAGE_MAX_AGE = 24 * 60 * 60 * 1000;
const DEFINITE_SEND_ERROR_CODES = new Set([
  "otp_delivery_failed",
  "otp_rate_limited",
  "otp_rate_limit_unavailable",
  "otp_cooldown",
]);

function emptyOtp(length: number): string[] {
  return Array<string>(length).fill("");
}

type Step = "phone" | "otp";
type DeliveryStatus = "accepted" | "unknown";
type OtpConfig = {
  codeLength: number;
  expiresIn: number;
  resendAfter: number;
};
type AuthUser = {
  id: number;
  isStaff: boolean;
};
type MeData = {
  user: AuthUser | null;
  otpConfig: OtpConfig;
};
type VerifyOtpData = {
  user: AuthUser;
};
type SendOtpData = {
  sent: boolean;
  expiresIn: number;
  resendAfter: number;
  codeLength: number;
  deliveryStatus?: DeliveryStatus;
};
type SendOtpErrorData = {
  activeChallenge?: boolean;
  expiresIn?: number;
  resendAfter?: number;
  codeLength?: number;
};
type VerifyOtpErrorData = {
  requiresNewCode?: boolean;
  resendAfter?: number;
};

const FALLBACK_OTP_CONFIG: OtpConfig = {
  codeLength: DEFAULT_OTP_LENGTH,
  expiresIn: FALLBACK_EXPIRES_IN,
  resendAfter: FALLBACK_RESEND_AFTER,
};

type StoredOtpUiState = {
  version: 2;
  step: "otp";
  phone: string;
  otpLength: number;
  resendDeadline: number;
  expiryDeadline: number;
  verifyDeadline: number | null;
  deliveryStatus: DeliveryStatus;
  savedAt: number;
};

function secondsUntil(deadline: number | null): number {
  return deadline ? Math.max(0, Math.ceil((deadline - Date.now()) / 1000)) : 0;
}

function positiveSeconds(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? Math.ceil(value)
    : fallback;
}

function validOtpLength(value: unknown, fallback: number): number {
  return Number.isInteger(value) &&
    Number(value) >= MIN_OTP_LENGTH &&
    Number(value) <= MAX_OTP_LENGTH
    ? Number(value)
    : fallback;
}

function normalizeOtpConfig(value: unknown): OtpConfig {
  const candidate =
    value && typeof value === "object"
      ? (value as Partial<OtpConfig>)
      : FALLBACK_OTP_CONFIG;

  return {
    codeLength: validOtpLength(
      candidate.codeLength,
      FALLBACK_OTP_CONFIG.codeLength
    ),
    expiresIn: positiveSeconds(
      candidate.expiresIn,
      FALLBACK_OTP_CONFIG.expiresIn
    ),
    resendAfter: positiveSeconds(
      candidate.resendAfter,
      FALLBACK_OTP_CONFIG.resendAfter
    ),
  };
}

function clearStoredOtpState() {
  try {
    sessionStorage.removeItem(OTP_STORAGE_KEY);
  } catch {
    // The flow still works when storage is unavailable.
  }
}

function storeOtpState(
  state: Omit<StoredOtpUiState, "version" | "step" | "savedAt">
) {
  try {
    const value: StoredOtpUiState = {
      version: 2,
      step: "otp",
      savedAt: Date.now(),
      ...state,
    };
    sessionStorage.setItem(OTP_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // The flow still works when storage is unavailable.
  }
}

function readStoredOtpState(): StoredOtpUiState | null {
  try {
    const raw = sessionStorage.getItem(OTP_STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<StoredOtpUiState>;
    const valid =
      value.version === 2 &&
      value.step === "otp" &&
      typeof value.phone === "string" &&
      isValidIranMobile(value.phone) &&
      Number.isInteger(value.otpLength) &&
      Number(value.otpLength) >= MIN_OTP_LENGTH &&
      Number(value.otpLength) <= MAX_OTP_LENGTH &&
      typeof value.resendDeadline === "number" &&
      Number.isFinite(value.resendDeadline) &&
      typeof value.expiryDeadline === "number" &&
      Number.isFinite(value.expiryDeadline) &&
      (value.verifyDeadline === null ||
        (typeof value.verifyDeadline === "number" &&
          Number.isFinite(value.verifyDeadline))) &&
      (value.deliveryStatus === "accepted" ||
        value.deliveryStatus === "unknown") &&
      typeof value.savedAt === "number" &&
      Date.now() - value.savedAt < OTP_STORAGE_MAX_AGE;

    if (!valid) {
      clearStoredOtpState();
      return null;
    }
    return value as StoredOtpUiState;
  } catch {
    clearStoredOtpState();
    return null;
  }
}

function formatCountdown(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deliveryStatus, setDeliveryStatus] =
    useState<DeliveryStatus>("accepted");
  const [loading, setLoading] = useState(false);
  const [storageReady, setStorageReady] = useState(false);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [otpConfig, setOtpConfig] = useState<OtpConfig>(FALLBACK_OTP_CONFIG);
  const [otpLength, setOtpLength] = useState(DEFAULT_OTP_LENGTH);
  const [otp, setOtp] = useState<string[]>(() => emptyOtp(DEFAULT_OTP_LENGTH));
  const [phoneRetryDeadline, setPhoneRetryDeadline] = useState<number | null>(
    null
  );
  const [resendDeadline, setResendDeadline] = useState<number | null>(null);
  const [expiryDeadline, setExpiryDeadline] = useState<number | null>(null);
  const [verifyDeadline, setVerifyDeadline] = useState<number | null>(null);
  const [resendSeconds, setResendSeconds] = useState(0);
  const [expirySeconds, setExpirySeconds] = useState(0);
  const [verifySeconds, setVerifySeconds] = useState(0);
  const [phoneRetrySeconds, setPhoneRetrySeconds] = useState(0);
  const otpRefs = useRef<Array<HTMLInputElement | null>>([]);
  const requestGeneration = useRef(0);
  const requestInFlight = useRef(false);
  const sessionCheckGeneration = useRef(0);

  /* eslint-disable react-hooks/set-state-in-effect -- localStorage is browser-only;
     this one-time effect restores the persisted OTP flow after hydration. */
  useEffect(() => {
    const stored = readStoredOtpState();
    if (stored) {
      setStep("otp");
      setPhone(stored.phone);
      setOtpLength(stored.otpLength);
      setOtp(emptyOtp(stored.otpLength));
      setResendDeadline(stored.resendDeadline);
      setExpiryDeadline(stored.expiryDeadline);
      setVerifyDeadline(stored.verifyDeadline);
      setDeliveryStatus(stored.deliveryStatus);
      if (stored.deliveryStatus === "unknown") {
        setNotice("درخواست ارسال ثبت شد؛ اگر پیامک رسید کد را وارد کنید.");
      }
      setResendSeconds(secondsUntil(stored.resendDeadline));
      setExpirySeconds(secondsUntil(stored.expiryDeadline));
      setVerifySeconds(secondsUntil(stored.verifyDeadline));
    }
    setStorageReady(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const checkSession = useCallback(() => {
    const requestId = ++sessionCheckGeneration.current;
    api.get<MeData>("/api/auth/me").then((response) => {
      if (requestId !== sessionCheckGeneration.current) return;
      if (response.ok && response.data) {
        setOtpConfig(normalizeOtpConfig(response.data.otpConfig));
      }
      if (response.ok && response.data?.user) {
        clearStoredOtpState();
        const destination = response.data.user.isStaff
          ? "/admin"
          : safeNextPath(
              new URLSearchParams(window.location.search).get("next")
            );
        router.replace(destination);
        return;
      }
      setSessionChecked(true);
    });
  }, [router]);

  useEffect(() => {
    checkSession();
    const onFocus = () => checkSession();
    window.addEventListener("focus", onFocus);
    const unsubscribeAuth = subscribeAuthChanged(checkSession);
    return () => {
      sessionCheckGeneration.current += 1;
      window.removeEventListener("focus", onFocus);
      unsubscribeAuth();
    };
  }, [checkSession]);

  useEffect(() => {
    const updateCountdowns = () => {
      setPhoneRetrySeconds(secondsUntil(phoneRetryDeadline));
      setResendSeconds(secondsUntil(resendDeadline));
      setExpirySeconds(secondsUntil(expiryDeadline));
      setVerifySeconds(secondsUntil(verifyDeadline));
    };
    updateCountdowns();
    const timer = window.setInterval(updateCountdowns, 1000);
    return () => window.clearInterval(timer);
  }, [phoneRetryDeadline, resendDeadline, expiryDeadline, verifyDeadline]);

  useEffect(() => {
    if (!storageReady) return;
    if (
      step === "otp" &&
      isValidIranMobile(phone) &&
      resendDeadline !== null &&
      expiryDeadline !== null
    ) {
      storeOtpState({
        phone,
        otpLength,
        resendDeadline,
        expiryDeadline,
        verifyDeadline,
        deliveryStatus,
      });
    } else if (step === "phone") {
      clearStoredOtpState();
    }
  }, [
    expiryDeadline,
    otpLength,
    phone,
    resendDeadline,
    step,
    storageReady,
    deliveryStatus,
    verifyDeadline,
  ]);

  useEffect(
    () => () => {
      requestGeneration.current += 1;
      requestInFlight.current = false;
    },
    []
  );

  function beginRequest(): number | null {
    if (requestInFlight.current) return null;
    requestInFlight.current = true;
    const requestId = ++requestGeneration.current;
    setLoading(true);
    return requestId;
  }

  function isCurrentRequest(requestId: number): boolean {
    return requestGeneration.current === requestId;
  }

  function finishRequest(requestId: number) {
    if (!isCurrentRequest(requestId)) return;
    requestInFlight.current = false;
    setLoading(false);
  }

  function applyOtpStep({
    normalizedPhone,
    codeLength,
    nextResendDeadline,
    nextExpiryDeadline,
    nextVerifyDeadline = null,
    nextDeliveryStatus = "accepted",
    nextNotice = "",
    clearCode = true,
  }: {
    normalizedPhone: string;
    codeLength: number;
    nextResendDeadline: number;
    nextExpiryDeadline: number;
    nextVerifyDeadline?: number | null;
    nextDeliveryStatus?: DeliveryStatus;
    nextNotice?: string;
    clearCode?: boolean;
  }) {
    setPhone(normalizedPhone);
    setOtpLength(codeLength);
    setOtp((current) =>
      clearCode || current.length !== codeLength ? emptyOtp(codeLength) : current
    );
    setPhoneRetryDeadline(null);
    setPhoneRetrySeconds(0);
    setResendDeadline(nextResendDeadline);
    setExpiryDeadline(nextExpiryDeadline);
    setVerifyDeadline(nextVerifyDeadline);
    setDeliveryStatus(nextDeliveryStatus);
    setResendSeconds(secondsUntil(nextResendDeadline));
    setExpirySeconds(secondsUntil(nextExpiryDeadline));
    setVerifySeconds(secondsUntil(nextVerifyDeadline));
    setError("");
    setNotice(nextNotice);
    setStep("otp");
    storeOtpState({
      phone: normalizedPhone,
      otpLength: codeLength,
      resendDeadline: nextResendDeadline,
      expiryDeadline: nextExpiryDeadline,
      verifyDeadline: nextVerifyDeadline,
      deliveryStatus: nextDeliveryStatus,
    });
  }

  async function sendOtp(requestedPhone: string): Promise<boolean> {
    const requestId = beginRequest();
    if (requestId === null) return false;

    const normalizedPhone = normalizeIranMobile(requestedPhone);
    const requestStartedAt = Date.now();
    const wasPhoneStep = step === "phone";
    const provisionalConfig = normalizeOtpConfig(otpConfig);
    const provisionalResendDeadline =
      requestStartedAt + provisionalConfig.resendAfter * 1000;
    const provisionalExpiryDeadline =
      requestStartedAt + provisionalConfig.expiresIn * 1000;

    setError("");
    if (wasPhoneStep) {
      setNotice("");
      setPhoneRetryDeadline(null);
      setPhoneRetrySeconds(0);
    }
    if (wasPhoneStep) {
      // If the page reloads while the provider request is in flight, the user can
      // still enter a code that may already have been delivered.
      storeOtpState({
        phone: normalizedPhone,
        otpLength: provisionalConfig.codeLength,
        resendDeadline: provisionalResendDeadline,
        expiryDeadline: provisionalExpiryDeadline,
        verifyDeadline: null,
        deliveryStatus: "unknown",
      });
    }

    const response = await api.post<SendOtpData, SendOtpErrorData>(
      "/api/auth/otp/send",
      { phone: normalizedPhone }
    );
    if (!isCurrentRequest(requestId)) return false;
    finishRequest(requestId);

    if (response.ok && response.data) {
      const codeLength = validOtpLength(
        response.data.codeLength,
        provisionalConfig.codeLength
      );
      const now = Date.now();
      const nextResendDeadline =
        now +
        positiveSeconds(
          response.data.resendAfter,
          provisionalConfig.resendAfter
        ) *
          1000;
      const nextExpiryDeadline =
        now +
        positiveSeconds(response.data.expiresIn, provisionalConfig.expiresIn) *
          1000;
      const nextDeliveryStatus: DeliveryStatus =
        response.data.deliveryStatus === "unknown" ? "unknown" : "accepted";
      applyOtpStep({
        normalizedPhone,
        codeLength,
        nextResendDeadline,
        nextExpiryDeadline,
        nextVerifyDeadline: wasPhoneStep ? null : verifyDeadline,
        nextDeliveryStatus,
        nextNotice:
          nextDeliveryStatus === "unknown"
            ? "درخواست ارسال ثبت شد؛ اگر پیامک رسید کد را وارد کنید."
            : "",
      });
      return true;
    }

    const errorData = response.errorData;
    const cooldownRetryAfter = positiveSeconds(errorData?.resendAfter, 0);
    const retryAfter =
      response.retryAfter ??
      (response.errorCode === "otp_cooldown" && cooldownRetryAfter > 0
        ? cooldownRetryAfter
        : undefined);
    const now = Date.now();

    if (
      response.status === 429 &&
      response.errorCode === "otp_cooldown" &&
      errorData?.activeChallenge === true
    ) {
      const codeLength = validOtpLength(
        errorData.codeLength,
        provisionalConfig.codeLength
      );
      const expiresIn = positiveSeconds(
        errorData.expiresIn,
        provisionalConfig.expiresIn
      );
      const resendAfter = positiveSeconds(
        errorData.resendAfter,
        retryAfter ?? provisionalConfig.resendAfter
      );
      applyOtpStep({
        normalizedPhone,
        codeLength,
        nextResendDeadline: now + resendAfter * 1000,
        nextExpiryDeadline: now + expiresIn * 1000,
        nextVerifyDeadline: wasPhoneStep ? null : verifyDeadline,
        nextDeliveryStatus: wasPhoneStep ? "unknown" : deliveryStatus,
        nextNotice: wasPhoneStep
          ? "کد قبلاً ارسال شده است؛ همان کد را وارد کنید."
          : notice || "کد فعال قبلی را وارد کنید.",
        clearCode: wasPhoneStep || codeLength !== otpLength,
      });
      return true;
    }

    const hasKnownDefiniteError =
      response.errorCode !== undefined &&
      DEFINITE_SEND_ERROR_CODES.has(response.errorCode);
    const transportOutcomeMayBeAmbiguous =
      !hasKnownDefiniteError &&
      (response.status === 0 ||
        (response.status >= 500 && response.status < 600) ||
        (response.status >= 200 && response.status < 300));
    if (transportOutcomeMayBeAmbiguous) {
      applyOtpStep({
        normalizedPhone,
        codeLength: provisionalConfig.codeLength,
        nextResendDeadline: provisionalResendDeadline,
        nextExpiryDeadline: provisionalExpiryDeadline,
        nextVerifyDeadline: wasPhoneStep ? null : verifyDeadline,
        nextDeliveryStatus: "unknown",
        nextNotice: "پاسخ ارسال دریافت نشد؛ اگر پیامک رسید کد را وارد کنید.",
      });
      return true;
    }

    if (retryAfter) {
      const nextDeadline = now + retryAfter * 1000;
      if (wasPhoneStep) {
        setPhoneRetryDeadline(nextDeadline);
        setPhoneRetrySeconds(secondsUntil(nextDeadline));
      } else {
        setResendDeadline(nextDeadline);
        setResendSeconds(secondsUntil(nextDeadline));
      }
    }

    if (wasPhoneStep) clearStoredOtpState();
    setError(response.error ?? "خطا در ارسال کد");
    return false;
  }

  async function submitPhone(event: React.FormEvent) {
    event.preventDefault();
    if (requestInFlight.current || phoneRetrySeconds > 0) return;

    const normalizedPhone = normalizeIranMobile(phone);
    if (!isValidIranMobile(normalizedPhone)) {
      setError("شماره موبایل را به‌درستی وارد کنید (مثال: ۰۹۱۲۱۲۳۴۵۶۷)");
      return;
    }

    if (await sendOtp(normalizedPhone)) {
      window.setTimeout(() => otpRefs.current[0]?.focus(), 50);
    }
  }

  function putDigits(startIndex: number, rawValue: string) {
    const digits = toEnglishDigits(rawValue).replace(/\D/g, "");
    setError("");

    if (!digits) {
      setOtp((current) => {
        const next = [...current];
        next[startIndex] = "";
        return next;
      });
      return;
    }

    setOtp((current) => {
      const next = [...current];
      digits
        .slice(0, otpLength - startIndex)
        .split("")
        .forEach((digit, offset) => {
          next[startIndex + offset] = digit;
        });
      return next;
    });
    const focusIndex = Math.min(startIndex + digits.length, otpLength - 1);
    otpRefs.current[focusIndex]?.focus();
  }

  function handleOtpKeyDown(index: number, event: React.KeyboardEvent) {
    if (event.key === "Backspace" && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  }

  function handleOtpPaste(event: React.ClipboardEvent) {
    event.preventDefault();
    putDigits(0, event.clipboardData.getData("text"));
  }

  function completeLogin(user: AuthUser) {
    clearStoredOtpState();
    notifyAuthChanged();
    const destination = user.isStaff
      ? "/admin"
      : safeNextPath(
          new URLSearchParams(window.location.search).get("next")
        );
    router.replace(destination);
  }

  async function submitOtp(event: React.FormEvent) {
    event.preventDefault();
    if (requestInFlight.current || verifySeconds > 0) return;

    if (otp.some((digit) => digit === "")) {
      setError(`کد ${otpLength} رقمی را کامل وارد کنید`);
      otpRefs.current[otp.findIndex((digit) => !digit)]?.focus();
      return;
    }
    if (expiryDeadline && expirySeconds <= 0) {
      setError("کد منقضی شده است؛ کد جدید درخواست کنید");
      return;
    }

    const requestId = beginRequest();
    if (requestId === null) return;
    setError("");
    const response = await api.post<VerifyOtpData, VerifyOtpErrorData>(
      "/api/auth/otp/verify",
      {
        phone: normalizeIranMobile(phone),
        code: otp.join(""),
      }
    );
    if (!isCurrentRequest(requestId)) return;

    const verificationOutcomeMayBeAmbiguous =
      response.status === 0 ||
      (response.status >= 500 && response.status < 600) ||
      (response.status >= 200 && response.status < 300);
    if (!response.ok && verificationOutcomeMayBeAmbiguous) {
      const session = await api.get<MeData>("/api/auth/me");
      if (!isCurrentRequest(requestId)) return;
      if (session.ok && session.data) {
        setOtpConfig(normalizeOtpConfig(session.data.otpConfig));
      }
      if (session.ok && session.data?.user) {
        finishRequest(requestId);
        completeLogin(session.data.user);
        return;
      }
    }

    finishRequest(requestId);

    if (
      !response.ok &&
      response.status === 400 &&
      response.errorCode === "otp_attempts_exhausted"
    ) {
      const now = Date.now();
      const serverResendAfter = response.errorData?.resendAfter;
      const resendAfter =
        typeof serverResendAfter === "number" &&
        Number.isFinite(serverResendAfter) &&
        serverResendAfter > 0
          ? Math.ceil(serverResendAfter)
          : 0;
      const nextResendDeadline = now + resendAfter * 1000;

      setOtp(emptyOtp(otpLength));
      setExpiryDeadline(now);
      setExpirySeconds(0);
      setVerifyDeadline(null);
      setVerifySeconds(0);
      setResendDeadline(nextResendDeadline);
      setResendSeconds(resendAfter);
      setNotice("");
      setError(
        response.error ??
          "این کد پس از ۵ تلاش ناموفق باطل شد؛ کد جدید درخواست کنید"
      );
      return;
    }

    if (!response.ok) {
      const retryAfter =
        response.retryAfter ?? (response.status === 429 ? 60 : undefined);
      if (retryAfter) {
        const nextDeadline = Date.now() + retryAfter * 1000;
        setVerifyDeadline(nextDeadline);
        setVerifySeconds(secondsUntil(nextDeadline));
      } else {
        setOtp(emptyOtp(otpLength));
        window.setTimeout(() => otpRefs.current[0]?.focus(), 0);
      }
      setError(response.error ?? "خطا در ورود");
      return;
    }

    if (response.data?.user) {
      completeLogin(response.data.user);
    }
  }

  async function resendOtp() {
    if (requestInFlight.current || resendSeconds > 0) return;
    if (await sendOtp(phone)) {
      window.setTimeout(() => otpRefs.current[0]?.focus(), 50);
    }
  }

  function editPhone() {
    if (requestInFlight.current) return;
    requestGeneration.current += 1;
    requestInFlight.current = false;
    clearStoredOtpState();
    setStep("phone");
    setOtpLength(otpConfig.codeLength);
    setOtp(emptyOtp(otpConfig.codeLength));
    setError("");
    setNotice("");
    setDeliveryStatus("accepted");
    setPhoneRetryDeadline(null);
    setResendDeadline(null);
    setExpiryDeadline(null);
    setVerifyDeadline(null);
    setResendSeconds(0);
    setExpirySeconds(0);
    setVerifySeconds(0);
    setPhoneRetrySeconds(0);
  }

  if (!storageReady || !sessionChecked) {
    return (
      <div
        role="status"
        className="grid min-h-[calc(100vh-200px)] place-items-center text-sm text-slate-400"
      >
        در حال بررسی وضعیت ورود...
      </div>
    );
  }

  const otpColumns = otpLength > 6 ? Math.ceil(otpLength / 2) : otpLength;
  const otpExpired = Boolean(expiryDeadline) && expirySeconds <= 0;
  const otpDescriptionIds = [
    notice ? "otp-notice" : "",
    error ? "otp-error" : otpExpired ? "otp-countdown" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const phoneDescriptionIds = [
    error ? "login-error" : "",
    phoneRetrySeconds > 0 ? "login-retry" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="flex min-h-[calc(100dvh-11rem)] items-center justify-center px-4 py-6 sm:min-h-[calc(100dvh-9rem)] sm:py-10">
      <div className="w-full max-w-md rounded-3xl border border-slate-100 bg-white p-5 shadow-sm min-[390px]:p-6 sm:p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <Image
            src="/brand/logo.png"
            alt="گروه صنعتی توانا"
            width={64}
            height={64}
            priority
            className="mb-3 h-16 w-16 object-contain"
          />
          <h1 className="text-xl font-bold text-slate-800">ورود | ثبت‌نام</h1>
          <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-500">
            {step === "phone" ? (
              "سلام!\nبرای ورود یا ثبت‌نام شماره موبایل خود را وارد کنید."
            ) : deliveryStatus === "unknown" ? (
              <>
                درخواست کد برای شماره <bdi dir="ltr">{phone}</bdi> ثبت شد.
              </>
            ) : (
              <>
                کد تأیید برای شماره <bdi dir="ltr">{phone}</bdi> پیامک شد.
              </>
            )}
          </p>
        </div>

        {step === "phone" && (
          <form onSubmit={submitPhone} aria-busy={loading} className="space-y-4">
            <div>
              <label
                htmlFor="login-phone"
                className="mb-1.5 block text-sm font-medium text-slate-600"
              >
                شماره موبایل
              </label>
              <input
                id="login-phone"
                name="phone"
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                dir="ltr"
                value={phone}
                disabled={loading}
                onChange={(event) => {
                  setPhone(event.target.value);
                  setError("");
                }}
                placeholder="09xxxxxxxxx"
                autoFocus
                aria-invalid={Boolean(error)}
                aria-describedby={phoneDescriptionIds || undefined}
                className={`w-full rounded-xl border bg-slate-50 px-4 py-3 text-center font-num tracking-widest outline-none transition focus:bg-white disabled:cursor-wait disabled:opacity-60 ${
                  error
                    ? "border-red-300 focus:border-red-400"
                    : "border-slate-200 focus:border-brand-400"
                }`}
              />
            </div>

            {error && (
              <p id="login-error" role="alert" className="text-xs text-red-500">
                {error}
              </p>
            )}

            {phoneRetrySeconds > 0 && (
              <p id="login-retry" className="text-xs text-amber-600">
                امکان تلاش مجدد تا{" "}
                <bdi dir="ltr" className="font-num">
                  {formatCountdown(phoneRetrySeconds)}
                </bdi>
              </p>
            )}

            <button
              type="submit"
              disabled={loading || phoneRetrySeconds > 0}
              className="w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading
                ? "در حال ارسال کد..."
                : phoneRetrySeconds > 0
                  ? "کمی صبر کنید"
                  : "دریافت کد ورود"}
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

        {step === "otp" && (
          <form onSubmit={submitOtp} aria-busy={loading} className="space-y-5">
            {notice && (
              <p
                id="otp-notice"
                role="status"
                className="rounded-xl bg-sky-50 px-4 py-2.5 text-center text-xs leading-6 text-sky-700"
              >
                {notice}
              </p>
            )}

            <fieldset disabled={loading || otpExpired}>
              <legend className="sr-only">کد تأیید {otpLength} رقمی</legend>
              <div
                dir="ltr"
                className="mx-auto grid gap-1 sm:gap-2"
                style={{
                  gridTemplateColumns: `repeat(${otpColumns}, minmax(0, 1fr))`,
                  maxWidth: `min(100%, ${otpColumns * 3.25}rem)`,
                }}
                onPaste={handleOtpPaste}
              >
                {otp.map((digit, index) => (
                  <input
                    key={index}
                    ref={(element) => {
                      otpRefs.current[index] = element;
                    }}
                    type="text"
                    inputMode="numeric"
                    autoComplete={index === 0 ? "one-time-code" : "off"}
                    maxLength={otpLength}
                    value={digit}
                    aria-label={`رقم ${index + 1} کد تأیید`}
                    aria-invalid={Boolean(error)}
                    aria-describedby={otpDescriptionIds || undefined}
                    onFocus={(event) => event.currentTarget.select()}
                    onChange={(event) => putDigits(index, event.target.value)}
                    onKeyDown={(event) => handleOtpKeyDown(index, event)}
                    className={`h-12 min-w-0 w-full rounded-xl border bg-slate-50 px-0 text-center text-base font-bold font-num outline-none transition focus:bg-white disabled:cursor-wait disabled:opacity-60 sm:text-lg ${
                      error
                        ? "border-red-300 focus:border-red-400"
                        : "border-slate-200 focus:border-brand-400"
                    }`}
                  />
                ))}
              </div>
            </fieldset>

            <div className="min-h-5 text-center text-xs">
              {error ? (
                <p id="otp-error" role="alert" className="text-red-500">
                  {error}
                </p>
              ) : otpExpired ? (
                <p id="otp-countdown" role="status" className="text-amber-600">
                  کد منقضی شده است؛ کد جدید بگیرید.
                </p>
              ) : (
                <p id="otp-countdown" className="text-slate-400">
                  اعتبار کد:{" "}
                  <bdi dir="ltr" className="font-num">
                    {formatCountdown(expirySeconds)}
                  </bdi>
                </p>
              )}
              {verifySeconds > 0 && (
                <p id="otp-verify-wait" className="mt-1 text-amber-600">
                  بررسی مجدد تا{" "}
                  <bdi dir="ltr" className="font-num">
                    {formatCountdown(verifySeconds)}
                  </bdi>
                </p>
              )}
            </div>

            <div className="text-center text-xs text-slate-500">
              {resendSeconds > 0 ? (
                <span>
                  ارسال مجدد تا{" "}
                  <bdi dir="ltr" className="font-num">
                    {formatCountdown(resendSeconds)}
                  </bdi>
                </span>
              ) : (
                <button
                  type="button"
                  disabled={loading}
                  onClick={resendOtp}
                  className="text-brand-600 hover:underline disabled:cursor-wait disabled:opacity-60"
                >
                  {otpExpired ? "دریافت کد جدید" : "ارسال مجدد کد تأیید"}
                </button>
              )}
              <span className="sr-only" aria-live="polite">
                {resendDeadline && resendSeconds === 0
                  ? "اکنون می‌توانید کد را دوباره ارسال کنید."
                  : ""}
              </span>
            </div>

            <button
              type="submit"
              disabled={
                loading ||
                verifySeconds > 0 ||
                otpExpired
              }
              className="w-full rounded-xl bg-brand-600 py-3 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading
                ? "در حال بررسی..."
                : verifySeconds > 0
                  ? "کمی صبر کنید"
                  : "تأیید و ورود"}
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={editPhone}
              className="w-full text-center text-xs text-slate-400 hover:text-slate-600 disabled:cursor-wait disabled:opacity-60"
            >
              ← ویرایش شماره موبایل
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
