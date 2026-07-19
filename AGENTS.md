<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `frontend/node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Project structure

- `frontend/` — Next.js 16 + Tailwind v4 storefront (Persian/RTL). All `/api/*` requests are proxied to the Django backend via `next.config.ts` rewrites.
- `backend/` — Django 6 + DRF API. Apps: `accounts` (phone OTP auth, custom User), `catalog` (categories/products/reviews), `carts` (guest+user carts), `orders`. Responses use `{ok: true, data}` / `{ok: false, error}`. Run inside `backend/venv`.
