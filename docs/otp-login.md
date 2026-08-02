# OTP login with IPPanel

The Django backend is the authentication authority. IPPanel only delivers an
SMS; it never validates a storefront user's code, and its API key never enters
the Next.js bundle or an API response.

## 1. IPPanel contract used by this project

The integration uses IPPanel Edge's approved-pattern endpoint:

```text
POST https://edge.ippanel.com/v1/api/send
Authorization: <raw API key, without "Bearer">
Content-Type: application/json
```

```json
{
  "sending_type": "pattern",
  "from_number": "+983000505",
  "code": "APPROVED_PATTERN_CODE",
  "recipients": ["+989121234567"],
  "params": {"code": "123456"}
}
```

The top-level `code` is the pattern identifier. `params.code` is the temporary
login code. The backend confirms acceptance only when the response is HTTP 200,
`meta.status` is `true`, and `data.message_outbox_ids` contains an ID.

Official references:

- [IPPanel API overview](https://docs.ippanel.com/docs/)
- [Send Pattern SMS](https://docs.ippanel.com/docs/send/pattern)
- [Create Pattern](https://docs.ippanel.com/docs/pattern/create-pattern)
- [Get Pattern By Code](https://docs.ippanel.com/docs/pattern/pattern-by-code)

Do not use IPPanel's `send_sms_otp` / `confirm_otp` panel-account endpoints for
store customers.

## 2. Create the pattern once

Create a normal pattern in IPPanel and wait for its status to become `active`.
For example:

```text
کد ورود ابزار سبز: %code%
این کد را در اختیار دیگران قرار ندهید.
```

Define `code` as the variable, copy the returned `pattern_code`, obtain a
non-expiring API key, and select a sender assigned to the account (for example
`+983000505`). Patterns are never created during a login request.

## 3. Install and configure

Install the backend dependencies and copy the example environment file:

```bash
cd backend
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Generate and store a production secret instead of reusing the example value:

```bash
./.venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Use at least these production values:

```dotenv
SECRET_KEY=<stable-random-secret-shared-by-all-replicas>
DJANGO_DEBUG=false
ALLOWED_HOSTS=shop.example.com
CSRF_TRUSTED_ORIGINS=https://shop.example.com
DATABASE_URL=postgresql://market:<password>@postgres.internal:5432/market?sslmode=require

OTP_SMS_BACKEND=ippanel
OTP_LENGTH=6
OTP_TTL_SECONDS=120
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=5
OTP_FAILURE_WINDOW_SECONDS=900
OTP_LOCKOUT_SECONDS=900
OTP_RETENTION_DAYS=7

IPPANEL_BASE_URL=https://edge.ippanel.com/v1
IPPANEL_API_KEY=<secret-api-key>
IPPANEL_FROM_NUMBER=+983000505
IPPANEL_PATTERN_CODE=<active-pattern-code>
IPPANEL_OTP_PARAMETER=code
IPPANEL_CONNECT_TIMEOUT=3
IPPANEL_READ_TIMEOUT=10

# Safe default. Change only after deploying a sanitizing trusted ingress.
TRUSTED_PROXY_COUNT=0
OTP_REQUIRE_SHARED_CACHE=true
REDIS_URL=redis://:<password>@redis.internal:6379/1
CACHE_KEY_PREFIX=market-production
```

The application fails closed when production has a placeholder secret, a
non-PostgreSQL/missing `DATABASE_URL`, a console SMS backend, incomplete IPPanel
settings, a non-HTTPS provider URL, or no shared Redis limiter. The IPPanel
timeouts are finite, capped, and must total less than the resend cooldown. Use
the TLS options required by your database host; `sslmode=require` is shown for a
remote PostgreSQL service.

Redis cannot be disabled when `DJANGO_DEBUG=false`. Use a dedicated, monitored Redis
database with `maxmemory-policy noeviction`; an eviction policy could discard a
live rate-limit bucket and restart its allowance. When Redis rejects writes or
is unavailable, OTP endpoints fail closed before IPPanel is called.

`TRUSTED_PROXY_COUNT` is safe only if neither Next.js nor Django can be reached
around a trusted ingress and that ingress strips client-supplied
`X-Forwarded-For` before rebuilding the chain. The bundled Next.js rewrite is
not a sanitizer: by itself it can preserve a caller-supplied value. Keep the
setting at `0` in that topology. After adding a sanitizing load balancer or
reverse proxy, set the exact value for its resulting header chain and verify it
with an end-to-end spoofing test; do not count Next.js merely because it proxies
`/api/*`. If Django sees only the Next.js peer while the value stays `0`, the IP
limit intentionally aggregates those users and may be overly restrictive; a
sanitized real-client chain is therefore part of a production deployment.

For local development only:

```dotenv
DJANGO_DEBUG=true
OTP_SMS_BACKEND=console
TRUSTED_PROXY_COUNT=0
```

The development code appears in the Django server log. It is never returned by
the API or rendered by the browser. The legacy `OTP_BYPASS` setting is not read
by the new implementation and should be removed from older `.env` files.

## 4. Migrate safely

Migration `0004_secure_otp_challenge`:

- canonicalizes existing user phones and stops if two accounts would collide;
- invalidates and deduplicates old short-lived OTP rows;
- removes the plaintext `code` column;
- adds salted hashes, pending-send state, lockout state, and provider metadata;
- adds database constraints for canonical `09xxxxxxxxx` identity values.

Because the old application expects the removed plaintext column, use a
roll-forward deployment:

1. Back up the database.
2. Put the old login endpoint in maintenance or stop old backend workers.
3. Install requirements and run `./.venv/bin/python manage.py migrate`.
4. Start only the new backend code, then the frontend.
5. Request a fresh OTP; pre-migration codes are intentionally invalid.

The schema migration can be reversed, but deleted plaintext values and duplicate
OTP rows cannot be recovered. Production requires PostgreSQL; SQLite remains a
development database and does not provide PostgreSQL's row-lock semantics. The
settings module refuses to start with SQLite when `DJANGO_DEBUG=false`.

## 5. Exact request and state flow

1. The browser fetches `GET /api/auth/csrf`; Django sets the CSRF cookie.
2. The browser posts a normalized phone to `/api/auth/otp/send` with
   `X-CSRFToken` and same-origin cookies.
3. Atomic Redis fixed-window counters limit both client IP and hashed phone.
   A database cooldown independently prevents two paid sends for one phone.
4. Django generates at least six cryptographically secure digits and computes a
   salted password hash. The plaintext exists only in process memory.
5. A short compare-and-set database write reserves a unique send token and its
   pending hash. The transaction ends before any network request.
6. Django calls IPPanel with separate connect/read timeouts and no automatic
   retry.
7. A confirmed acceptance atomically promotes the pending hash and stores the
   outbox ID. An explicit rejection clears only this reservation, preserving an
   older usable code. A read timeout, connection drop, HTTP timeout, or provider
   5xx is ambiguous, so the exact pending code remains verifiable with status
   `unknown`; this prevents an immediate duplicate SMS. A still-valid pending
   code cannot be overwritten by a resend.
8. The browser posts the digits to `/api/auth/otp/verify`. A row lock atomically
   counts failures and consumes a matching active or pending hash once. Success
   also revokes any concurrent reservation, so its finalizer cannot resurrect a
   second usable code.
9. Failed attempts survive resends. Five failures within the configured window
   start a timed lockout; a new code does not reset that counter.
10. Django creates/reuses the canonical phone user, calls `login()` (rotating the
    session key), records `auth_method=otp`, and transactionally merges the guest
    cart. A transient cart merge error cannot undo a successful login.
11. The frontend clears the OTP from memory, synchronizes auth state across tabs,
    and redirects only to a validated same-origin path.

No database lock is held during the IPPanel call. The pending hash also means a
code can still be checked if IPPanel accepted it but final database promotion
temporarily failed.

## 6. API and frontend behavior

A confirmed send returns HTTP 200. An ambiguous provider result returns HTTP
202 with the same safe shape and `deliveryStatus: "unknown"`:

```json
{
  "ok": true,
  "data": {
    "sent": true,
    "expiresIn": 120,
    "resendAfter": 60,
    "codeLength": 6,
    "deliveryStatus": "accepted"
  }
}
```

The frontend tells the user to enter the code if it arrives after an ambiguous
send. It supports Persian/Arabic digit input, paste and SMS autofill, responsive
6–10 digit layouts, expiry/resend/verification timers, and safe `next` redirects.
Only non-secret challenge UI state is kept in `sessionStorage`; OTP digits are
never persisted.

`GET /api/auth/me` includes public UI configuration (`codeLength`, `expiresIn`,
and `resendAfter`) even before login, so lost-response recovery follows the
backend's configured values. Error responses use stable codes such as
`otp_cooldown`, `otp_rate_limited`, `otp_locked`, `otp_invalid`, and
`otp_delivery_failed`. Only `otp_cooldown` with `activeChallenge: true` tells the
browser that a verifiable challenge exists; an ordinary throttle never pretends
that a message was sent.

Provider details, credentials, hashes, OTP digits, and internal exceptions are
never exposed. Cooldown/lockout/cache throttles return `Retry-After`.

## 7. Abuse, storage, and operations

The shipped limiter uses atomic cache `add`/`incr`, not DRF's non-atomic request
history. Redis is required and shared by all production workers/replicas; if it
is unavailable, OTP traffic fails closed with 503 rather than sending unmetered
SMS. Phone/IP values are represented by keyed hashes in cache keys. The
per-phone database cooldown and one-time consumption provide independent
protection.

Run the retention command daily (cron, systemd timer, or the deployment's job
scheduler):

```bash
./.venv/bin/python manage.py purge_otps
```

It removes expired diagnostic rows older than `OTP_RETENTION_DAYS`, including
stale pending/finalization-failure rows and their phone/outbox metadata.
`--days N` is available for an explicit retention period.

SMS OTP currently gives the project's staff users the same authenticated Django
session used by the custom Next.js admin dashboard. For a high-value production
admin, require a password/TOTP or WebAuthn step-up and check the recorded
`auth_method`; SMS alone should not be treated as phishing-resistant MFA.

## 8. Verification checklist

The test suite mocks IPPanel and never sends paid/network SMS:

```bash
cd backend
env DJANGO_DEBUG=true OTP_SMS_BACKEND=console ./.venv/bin/python manage.py test
./.venv/bin/python manage.py makemigrations --check --dry-run
```

Coverage includes the exact provider payload/header, strict envelopes, definite
versus ambiguous failures, hash-only storage, provider I/O outside transactions,
pending-state recovery, failed-resend preservation, concurrent
verification/resend revocation, cooldown metadata, rolling attempts, lockout,
expiry, one-time use, Unicode phone rejection, CSRF, atomic throttles, sessions,
non-fatal cart merge, stale-pending retention, and secret-free API responses.

Before enabling real traffic, send once to a controlled phone and verify:

- the pattern is `active` and `%code%` exactly matches the configured parameter;
- sender and recipient are accepted in E.164 form;
- IPPanel credit and delivery reports are correct;
- HTTPS, Secure session/CSRF cookies, and proxy headers work end to end;
- every replica shares the stable `SECRET_KEY`, PostgreSQL, and Redis;
- a timeout is not automatically retried;
- the daily `purge_otps` job runs and is monitored.
