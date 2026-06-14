import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // ریشه‌ی workspace را به همین پوشه محدود می‌کند تا هشدار چند lockfile رفع شود
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
