# Green Tools Market

Green Tools Market is a Persian, right-to-left e-commerce application for agricultural tools and supplies. It combines a Next.js storefront and management dashboard with a Django REST API.

## Technology stack

- **Frontend:** Next.js 16, React 19, TypeScript, and Tailwind CSS 4
- **Backend:** Django 6 and Django REST Framework
- **Development database:** SQLite
- **Production database:** PostgreSQL
- **Authentication:** Phone-number OTP with console and IPPanel SMS backends
- **API documentation:** OpenAPI, Swagger UI, and ReDoc

## Repository structure

```text
Market/
├── backend/    # Django API, business logic, database, and media files
├── frontend/   # Next.js storefront and management dashboard
└── docs/       # Feature-specific documentation
```

The frontend proxies `/api/*`, `/media/*`, `/robots.txt`, and `/sitemap.xml` requests to Django. This keeps session cookies and CSRF handling on the same browser origin during normal storefront use.

## Features

- Product catalog, categories, brands, specifications, reviews, and comparisons
- Guest and authenticated shopping carts
- Checkout, order management, and printable invoices
- Phone-number OTP authentication
- Customer profiles, addresses, favorites, comments, and order history
- Blog, static pages, homepage sections, SEO settings, and sitemap management
- Configurable footer, contact details, location map, and floating contact buttons
- Role-based storefront management dashboard

## Prerequisites

Install the following before starting:

- Python 3.12 or newer
- Node.js 20.9 or newer
- npm

PostgreSQL and Redis are required for production deployments but are optional for local development.

## Local development

### 1. Start the backend

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_catalog
python manage.py runserver 127.0.0.1:8000
```

On Windows, activate the virtual environment with `.venv\Scripts\activate` and use `copy .env.example .env` instead of `cp`.

The default development configuration uses SQLite. Replace `SECRET_KEY` in `backend/.env` with a private random value before using the application outside local development.

Optional backend commands:

```bash
# Create a Django superuser
python manage.py createsuperuser

# Add richer demo content; this downloads product images
python manage.py seed_demo
```

### 2. Start the frontend

Open another terminal at the repository root:

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

On Windows, use `copy .env.example .env` instead of `cp`.

Open the following services:

- Storefront: <http://localhost:3000>
- Store management dashboard: <http://localhost:3000/admin>
- Django administration: <http://127.0.0.1:8000/admin/>
- Swagger API documentation: <http://127.0.0.1:8000/api/docs/>
- ReDoc API documentation: <http://127.0.0.1:8000/api/redoc/>
- OpenAPI schema: <http://127.0.0.1:8000/api/schema/>

## Environment configuration

The example environment files document all supported settings:

- `backend/.env.example`
- `frontend/.env.example`

Important frontend settings include:

- `BACKEND_URL`: Django server used by the Next.js proxy
- `SITE_URL`: Public storefront URL used for canonical and Open Graph metadata
- `FRONTEND_REVALIDATE_SECRET`: Shared secret for on-demand cache revalidation
- `GOOGLE_MAPS_EMBED_API_KEY`: Optional key for the official Google Maps embed route

Important backend settings include:

- `SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`: PostgreSQL connection URL required in production
- `REDIS_URL`: Redis connection URL required for production OTP throttling
- `OTP_SMS_BACKEND`: Use `console` locally or `ippanel` in production
- `IPPANEL_*`: IPPanel credentials, sender number, pattern codes, and timeouts
- `FRONTEND_REVALIDATE_URL` and `FRONTEND_REVALIDATE_SECRET`: Frontend cache invalidation settings

## OTP authentication

Local development defaults to `OTP_SMS_BACKEND=console`. OTP codes are written to the Django server log and are never returned by the API.

Production uses the IPPanel pattern API. See [OTP Login and IPPanel Setup](docs/otp-login.md) for configuration, architecture, database migration, security behavior, and deployment guidance.

## Cache revalidation

Footer content is cached by the storefront. To make dashboard changes visible immediately in production, configure the same secret on both applications:

```dotenv
# backend/.env
FRONTEND_REVALIDATE_URL=https://example.com/internal/revalidate
FRONTEND_REVALIDATE_SECRET=replace-with-a-long-random-secret

# frontend/.env
FRONTEND_REVALIDATE_SECRET=replace-with-the-same-secret
```

Without these values, the footer still works but may remain cached for up to one minute after an update.

## API conventions

Successful API responses use this envelope:

```json
{"ok": true, "data": {}}
```

Errors use this envelope:

```json
{"ok": false, "error": "A human-readable message", "errorCode": "optional_code", "data": {}}
```

See [Blog API](docs/blog-api.md) for the blog endpoint reference.

## Quality checks

Run the backend test suite:

```bash
cd backend
source .venv/bin/activate
python manage.py test
```

Run frontend linting and create a production build:

```bash
cd frontend
npm run lint
npm run build
```

## Production notes

When `DJANGO_DEBUG=false`, the backend enforces several production safeguards:

- `SECRET_KEY` must be strong and unique.
- `DATABASE_URL` must point to PostgreSQL.
- `REDIS_URL` must be configured for shared, atomic OTP throttling.
- `OTP_SMS_BACKEND` must be `ippanel` with valid provider settings.
- HTTPS cookies, HSTS, and secure redirect settings are enabled by default.

Set `SITE_URL` to the public storefront URL so canonical links and Open Graph metadata use the correct origin. Run database migrations during every deployment.
