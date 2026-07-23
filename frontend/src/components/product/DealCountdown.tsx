"use client";

import { useEffect, useState } from "react";

// شمارش معکوس تا پایان روز (تخفیف‌های شگفت‌انگیز روزانه)
export default function DealCountdown() {
  const [left, setLeft] = useState<{ h: string; m: string; s: string } | null>(
    null
  );

  useEffect(() => {
    function tick() {
      const now = new Date();
      const end = new Date(now);
      end.setHours(23, 59, 59, 999);
      const diff = Math.max(0, end.getTime() - now.getTime());
      const totalSeconds = Math.floor(diff / 1000);
      const pad = (n: number) =>
        String(n).padStart(2, "0").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[+d]);
      setLeft({
        h: pad(Math.floor(totalSeconds / 3600)),
        m: pad(Math.floor((totalSeconds % 3600) / 60)),
        s: pad(totalSeconds % 60),
      });
    }
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  if (!left) {
    return <div className="h-9" />;
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-white/90">پایان تخفیف‌ها تا</span>
      <div className="flex items-center gap-1" dir="ltr">
        {[left.h, left.m, left.s].map((part, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <span className="text-white/70">:</span>}
            <span className="grid h-8 w-9 place-items-center rounded-lg bg-white/20 text-sm font-bold text-white font-num backdrop-blur">
              {part}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
