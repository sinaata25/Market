"use client";

import { useState } from "react";

export default function ProductGallery({
  images = [],
  title = "",
}: {
  images?: string[];
  title?: string;
}) {
  const [active, setActive] = useState(0);

  if (images.length === 0) return null;

  return (
    <div className="lg:sticky-below-header">
      <div className="aspect-square overflow-hidden rounded-2xl border border-slate-100 bg-slate-50">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={images[Math.min(active, images.length - 1)]}
          alt={title}
          className="h-full w-full object-contain"
        />
      </div>

      {images.length > 1 && (
        <div className="responsive-scroll mt-3 flex justify-start gap-2 pb-1 sm:justify-center">
          {images.map((src, i) => (
            <button
              key={src}
              onClick={() => setActive(i)}
              aria-label={`نمایش تصویر ${i + 1} از ${images.length}`}
              className={`h-16 w-16 shrink-0 overflow-hidden rounded-xl border transition ${
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
