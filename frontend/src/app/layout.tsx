import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import CompareTray from "@/components/product/CompareTray";

// فونت فارسی وزیرمتن — به‌صورت محلی host می‌شود (بدون وابستگی به اینترنت)
const vazirmatn = localFont({
  src: [
    { path: "../../public/fonts/Vazirmatn-Regular.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/Vazirmatn-Medium.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/Vazirmatn-Bold.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-vazirmatn",
  display: "swap",
  fallback: ["Tahoma", "Arial", "sans-serif"],
});

export const metadata: Metadata = {
  title: "گروه صنعتی توانا | فروشگاه اینترنتی ابزارآلات کشاورزی",
  description:
    "گروه صنعتی توانا؛ فروشگاه اینترنتی ابزارآلات و ادوات کشاورزی. خرید آنلاین انواع ابزار باغبانی، سمپاش، اره‌موتوری و ماشین‌آلات کشاورزی با ارسال به سراسر کشور.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl" className={`${vazirmatn.variable} h-full`}>
      <body className="min-h-full flex flex-col bg-background text-foreground antialiased font-sans">
        <Header />
        <main className="flex-1 pb-20">{children}</main>
        <Footer />
        <CompareTray />
      </body>
    </html>
  );
}
