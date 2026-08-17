# Accounts app contributor guide

## Responsibility

`accounts` owns the custom phone-number user, OTP session login, user profile,
addresses, favorites, and the user's review-management endpoints. Authentication
uses Django sessions, not JWTs. Every mutating browser request is therefore
expected to pass Django's CSRF protection.

## Module map

- `models.py` defines `User`, `Address`, `Favorite`, and the persistent `Otp`
  challenge state.
- `otp.py` is the concurrency-safe OTP state machine. Keep provider network I/O
  outside database transactions.
- `sms.py` isolates SMS providers and classifies definite versus ambiguous
  delivery failures.
- `throttles.py` implements atomic fixed-window limits by IP and phone.
- `views.py` exposes authentication and session endpoints.
- `views_profile.py` exposes profile, address, favorite, and personal-review APIs.
- `schema.py` teaches drf-spectacular that session authentication requires both
  a CSRF cookie and header.
- `admin.py` configures Django admin without exposing OTP hashes.
- `management/commands/` contains role-management and OTP-retention commands.
- `tests.py` is the main behavioral and concurrency specification.

## Models and invariants

### `UserManager` and `User`

`UserManager` normalizes phone lookup arguments in `get_or_create()` and
`update_or_create()`. This matters because `0912…`, Persian digits, and other
accepted display forms must resolve to one canonical database identity.
`create_user()` validates the normalized Iranian mobile and assigns an unusable
password when no password is supplied: normal customers authenticate only by
OTP. `create_superuser()` additionally enforces both staff flags.

`User` replaces Django's username with the unique `phone` field via
`USERNAME_FIELD`. Its `save()` repeats normalization and validation so direct
ORM writes cannot bypass the manager. The database check constraint is a final
canonical-format defense. Keep all three layers: caller validation gives good
errors, `save()` protects Python writes, and the constraint protects the data.

`is_staff` grants the full custom admin API. `is_seo_manager` grants only the SEO
API. Do not conflate these roles.

### `Address` and `Favorite`

Addresses cascade with their user and are ordered with defaults first. Application
logic in `apply_address()` ensures only one address is marked default at a time.
Favorites cascade with user/product and have a database unique constraint on the
pair; the API treats an existing favorite idempotently.

### `Otp`

There is exactly one row per phone. Active fields (`code_hash`, expiry, attempts,
used) represent the currently usable code. Pending fields represent a resend that
was reserved before contacting the provider. `send_token` is a compare-and-set
token preventing a delayed sender from overwriting newer state.

Only hashes are stored. `pending_code_hash` is deliberately persisted before the
SMS call: if the provider accepts the message but its response or the final DB
write fails, the delivered code can still be verified. `resend_blocked_until`
also prevents blind duplicate sends after an ambiguous result.

## OTP flow

### Issuing a code

`issue_otp()` generates a non-leading-zero code with `secrets`, hashes it, and
reserves a send through `_reserve_send()`. Reservation uses short locked database
operations and compare-and-set conditions. SQLite lock retries exist only for
local development/tests; production requires PostgreSQL row locking.

The SMS call happens after the reservation transaction closes. This is crucial:
holding a database lock during a slow network request would serialize unrelated
logins and amplify provider outages.

- A definite provider failure releases the reservation so a safe retry is possible.
- An ambiguous failure keeps the pending code and cooldown because the SMS may
  already have been delivered.
- `_finalize_send()` promotes pending state only if its token is still current.
  A verification or newer reservation therefore cannot be resurrected by an old
  worker.

`OtpIssueResult` is an immutable service DTO carrying expiry, cooldown, and
delivery status back to the view.

### Verifying a code

`verify_otp()` locks the phone's row and checks both active and pending candidates.
Hashes are compared with Django's password-hash helper. Wrong attempts are counted
per candidate; exhausting the configured limit consumes that code. Expired and
used codes cannot authenticate. A successful verification atomically consumes
the challenge, creates or retrieves the canonical user, rejects inactive users,
and returns the user to the view.

Do not move authentication/session creation into `otp.py`: the service owns OTP
state, while `views.py` owns the HTTP session and guest-cart merge.

## SMS abstraction

`SmsDeliveryResult` is a frozen DTO containing the provider message ID.
`SmsDeliveryError` means the send definitely failed and a retry is safe.
`SmsDeliveryUncertain` means the provider may have accepted it; callers must not
immediately resend. `IPPanelSmsBackend` sends the provider's documented pattern
payload, uses separate connect/read timeouts, validates the success envelope, and
never returns provider internals to the client. Phone numbers are masked in logs.
`send_pattern_sms()` is the shared approved-pattern entry point; the OTP helper is
a compatibility wrapper around it. The console backend is development-only and is
rejected by production settings.

## Throttling and CSRF

OTP endpoints apply separate IP and normalized-phone limits. Cache identifiers
are HMACed so shared Redis keys do not expose enumerable phones/IPs. The limiter
uses atomic `add`/`incr` instead of DRF's history-list algorithm. It fails closed
with 503 if cache is unavailable because SMS sends cost money and are abuse-prone.

`CsrfProtectedSessionAuthentication` forces CSRF checks even before a user is
authenticated. `OtpCsrfRequired` makes that requirement explicit on OTP routes.
The client first calls `GET /api/auth/csrf`, then echoes the cookie value in
`X-CSRFToken` for mutations.

## Endpoints

All paths below are under `/api/auth/`.

- `GET csrf`: set and return the CSRF token.
- `POST otp/send`: validate/normalize a phone and reserve/send a code.
- `POST otp/verify`: verify, create a session, and merge the guest cart.
- `GET me`: return the current public user plus public OTP UI timing settings.
- `POST logout`: end the session.
- `GET/PATCH profile`: profile summary or name update.
- `GET/POST addresses`, `PATCH/DELETE addresses/<id>`: owned addresses only.
- `GET/POST favorites`, `GET favorites/<product-id>`: list/add/check favorites.
- `GET/DELETE my-comments`: list or delete the authenticated user's own comments,
  questions, and replies with moderation and verified-purchase state.

Serializers validate request input. The `*ResponseSerializer` classes mainly
document response envelopes for OpenAPI; response dictionaries are produced by
`ok()`/`fail()` and DTO helpers.

## Commands

- `python manage.py make_admin PHONE [--revoke]`
- `python manage.py make_seo PHONE [--revoke]`
- `python manage.py purge_otps` removes only retention-eligible inactive/stale
  rows; active challenges must survive cleanup.

## Safe change checklist

1. Preserve canonical phone handling in manager, model, serializer, and throttle.
2. Never store or log plaintext OTPs outside the development console backend.
3. Never perform provider I/O while a database transaction/row lock is open.
4. Treat timeouts after connection as ambiguous unless provider idempotency exists.
5. Keep CSRF and both throttle dimensions on send and verify endpoints.
6. Query profile resources through `request.user` to prevent horizontal access.
7. Run `./.venv/bin/python manage.py test accounts --verbosity 2`.
