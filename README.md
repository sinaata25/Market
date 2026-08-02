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

## نکته‌ها

- در توسعه، `OTP_SMS_BACKEND=console` کد را فقط در لاگ جنگو می‌نویسد؛ کد هیچ‌گاه در API برنمی‌گردد.
- دیتابیس توسعه SQLite است (`backend/db.sqlite3`)؛ استقرار با `DJANGO_DEBUG=false` فقط با `DATABASE_URL` از نوع PostgreSQL بالا می‌آید.
- قرارداد پاسخ همه‌ی APIها: `{ok: true, data}` یا `{ok: false, error, errorCode?, data?}`.
