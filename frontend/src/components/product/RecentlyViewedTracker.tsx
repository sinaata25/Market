"use client";

import { useEffect } from "react";
import { recordRecentlyViewed } from "@/lib/recently-viewed";

export default function RecentlyViewedTracker({ productId }: { productId: number }) {
  useEffect(() => {
    recordRecentlyViewed(productId);
  }, [productId]);

  return null;
}
