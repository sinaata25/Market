"use client";

import { useState } from "react";

export default function BlogImage({
  src,
  alt,
  className = "",
}: {
  src: string | null;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <span
        role="img"
        aria-label={src ? "تصویر در دسترس نیست" : "نوشته بدون تصویر شاخص"}
        className={`grid place-items-center bg-gradient-to-br from-brand-50 to-slate-100 text-5xl ${className}`}
      >
        🌱
      </span>
    );
  }
  return (
    // Media is same-origin through the existing Django rewrite.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      className={className}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
