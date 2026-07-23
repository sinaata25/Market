"use client";

import { useState } from "react";

// گالری تصویر محصول؛ اگر عکس واقعی نبود از اموجی استفاده می‌شود
export default function ProductGallery({
  emoji,
  images = [],
  title = "",
}: {
  emoji: string;
  images?: string[];
  title?: string;
}) {
  const [active, setActive] = useState(0);
  const hasImages = images.length > 0;

  return (
    <div className="lg:sticky lg:top-28">
      <div className="grid aspect-square place-items-center overflow-hidden rounded-2xl border border-slate-100 bg-slate-50 text-[8rem]">
        {hasImages ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={images[Math.min(active, images.length - 1)]}
            alt={title}
            className="h-full w-full object-contain"
          />
        ) : (
          emoji
        )}
      </div>

      {hasImages && images.length > 1 && (
        <div className="mt-3 flex justify-center gap-2">
          {images.map((src, i) => (
            <button
              key={src}
              onClick={() => setActive(i)}
              className={`h-16 w-16 overflow-hidden rounded-xl border transition ${
                active === i
                  ? "border-brand-500"
                  : "border-slate-200 hover:border-brand-300"
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={src}
                alt=""
                className="h-full w-full object-cover"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
