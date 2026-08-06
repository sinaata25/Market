import Link from "next/link";

const columns = [
  {
    title: "گروه صنعتی توانا",
    links: [
      { label: "درباره ما", href: "#" },
      { label: "تماس با ما", href: "#" },
      { label: "فرصت‌های شغلی", href: "#" },
      { label: "وبلاگ کشاورزی", href: "/blog" },
    ],
  },
  {
    title: "خدمات مشتریان",
    links: ["پاسخ به پرسش‌ها", "رویه ارسال سفارش", "شرایط بازگشت کالا", "حریم خصوصی"].map((label) => ({ label, href: "#" })),
  },
  {
    title: "راهنمای خرید",
    links: ["نحوه ثبت سفارش", "شیوه‌های پرداخت", "رهگیری سفارش", "گارانتی محصولات"].map((label) => ({ label, href: "#" })),
  },
];

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-10">
        {/* مزیت‌ها */}
        <div className="grid grid-cols-2 gap-4 border-b border-slate-100 pb-8 text-center sm:grid-cols-4">
          {[
            { icon: "🚚", text: "ارسال به سراسر کشور" },
            { icon: "✅", text: "ضمانت اصالت کالا" },
            { icon: "💳", text: "پرداخت امن و درب منزل" },
            { icon: "🎧", text: "پشتیبانی ۷ روز هفته" },
          ].map((f) => (
            <div key={f.text} className="flex flex-col items-center gap-2">
              <span className="text-3xl">{f.icon}</span>
              <span className="text-sm text-slate-600">{f.text}</span>
            </div>
          ))}
        </div>

        {/* ستون‌ها */}
        <div className="grid grid-cols-2 gap-8 py-8 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <div className="mb-3 flex items-center gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-lg">
                🌾
              </span>
              <span className="text-lg font-bold text-brand-700">
                گروه صنعتی توانا
              </span>
            </div>
            <p className="text-sm leading-7 text-slate-500">
              فروشگاه اینترنتی ابزارآلات و ادوات کشاورزی؛ ارائه‌دهنده انواع ابزار
              باغبانی، سمپاش و ماشین‌آلات با بهترین قیمت و ضمانت اصالت کالا.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <h3 className="mb-3 font-bold text-slate-700">{col.title}</h3>
              <ul className="space-y-2 text-sm text-slate-500">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link href={link.href} className="transition hover:text-brand-700">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-slate-100 pt-6 text-center text-xs text-slate-400">
          © {new Date().getFullYear()} گروه صنعتی توانا — تمامی حقوق محفوظ است.
        </div>
      </div>
    </footer>
  );
}
