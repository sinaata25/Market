# 🌾 ابزار سبز — فروشگاه اینترنتی ابزارآلات کشاورزی

فروشگاه فارسی (RTL) با فرانت **Next.js + Tailwind** و بک‌اند **Django + DRF**.

```
market/
├── frontend/   # Next.js 16 — رابط کاربری (پورت 3000)
└── backend/    # Django 6 + DRF — API و دیتابیس (پورت 8000)
```

درخواست‌های `/api/*` فرانت از طریق rewrite در `next.config.ts` به جنگو پروکسی می‌شوند.

## راه‌اندازی بک‌اند

```powershell
cd backend
py -3.13 -m venv venv              # فقط بار اول
.\venv\Scripts\pip install -r requirements.txt
copy .env.example .env             # و مقداردهی SECRET_KEY
.\venv\Scripts\python manage.py migrate
.\venv\Scripts\python manage.py seed_catalog
.\venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

پنل ادمین: `python manage.py createsuperuser` سپس http://127.0.0.1:8000/admin

## راه‌اندازی فرانت (ترمینال دوم)

```powershell
cd frontend
npm install                        # فقط بار اول
copy .env.example .env             # BACKEND_URL پیش‌فرض درست است
npm run dev
```

سایت: http://localhost:3000

## ورود با OTP و IPPanel

سیستم OTP به API الگوی IPPanel متصل است. راهنمای ساخت الگو، تنظیم `.env`،
مهاجرت دیتابیس، معماری و چک‌لیست استقرار در [docs/otp-login.md](docs/otp-login.md) آمده است.

## فوتر

ساختار و محتوای فوتر از `/admin/footer` مدیریت می‌شود و فروشگاه آن را از
`GET /api/footer` می‌خواند.

در حالت توسعه، فوتر کش نمی‌شود و هر تغییر مدیر با همان یک بار بارگذاری دیده
می‌شود. در **استقرار تولید** این دو مقدار را در دو طرف تنظیم کنید تا تغییر
مدیر بلافاصله در فروشگاه دیده شود:

```
# backend/.env
FRONTEND_REVALIDATE_URL=https://example.com/internal/revalidate
FRONTEND_REVALIDATE_SECRET=<یک رشته‌ی تصادفی بلند>

# frontend/.env
FRONTEND_REVALIDATE_SECRET=<همان رشته>
```

بدون این دو، فروشگاه هنوز درست کار می‌کند اما فوتر تا یک دقیقه پس از هر
تغییر، نسخه‌ی کش‌شده را نشان می‌دهد.

## نکته‌ها

- در توسعه، `OTP_SMS_BACKEND=console` کد را فقط در لاگ جنگو می‌نویسد؛ کد هیچ‌گاه در API برنمی‌گردد.
- دیتابیس توسعه SQLite است (`backend/db.sqlite3`)؛ استقرار با `DJANGO_DEBUG=false` فقط با `DATABASE_URL` از نوع PostgreSQL بالا می‌آید.
- قرارداد پاسخ همه‌ی APIها: `{ok: true, data}` یا `{ok: false, error, errorCode?, data?}`.

## وبلاگ

صفحات عمومی وبلاگ در `/blog` و `/blog/{slug}` و مدیریت نوشته‌ها در
`/admin/blog` قرار دارد. پس از دریافت تغییرات جدید، مهاجرت‌ها را اجرا کنید:

```powershell
cd backend
.\venv\Scripts\python manage.py migrate
```

برای canonical و Open Graph URL در فرانت، مقدار `SITE_URL` را در محیط استقرار
برابر آدرس عمومی سایت قرار دهید. مستندات endpointها در
[`docs/blog-api.md`](docs/blog-api.md) آمده است.
