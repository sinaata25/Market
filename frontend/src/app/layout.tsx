import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

export const metadata: Metadata = {
  title: "ابزار سبز | فروشگاه اینترنتی ابزارآلات کشاورزی",
  description:
    "فروشگاه اینترنتی ابزارآلات و ادوات کشاورزی؛ خرید آنلاین انواع ابزار باغبانی، سمپاش، اره‌موتوری و ماشین‌آلات کشاورزی با ارسال به سراسر کشور.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl" className="h-full">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-800 antialiased font-sans">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
