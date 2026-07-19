"use client";

import { useState } from "react";

// گالری تصویر محصول؛ چون تصویر واقعی نداریم از اموجی روی پس‌زمینه استفاده می‌کنیم
export default function ProductGallery({ emoji }: { emoji: string }) {
  const [active, setActive] = useState(0);
  const thumbs = [emoji, emoji, emoji, emoji];

  return (
    <div className="lg:sticky lg:top-28">
      <div className="grid aspect-square place-items-center rounded-2xl border border-slate-100 bg-slate-50 text-[8rem]">
        {emoji}
      </div>
      <div className="mt-3 flex justify-center gap-2">
        {thumbs.map((t, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            className={`grid h-16 w-16 place-items-center rounded-xl border text-2xl transition ${
              active === i
                ? "border-brand-500 bg-brand-50"
                : "border-slate-200 bg-white hover:border-brand-300"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}
