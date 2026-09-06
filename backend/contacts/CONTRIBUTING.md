# Floating contact buttons

This feature follows the existing Django app → selector/service → DTO/API pattern.
The Persian dashboard is at `/admin/floating-contact-buttons`, labelled
**دکمه‌های تماس شناور** in the shop admin menu. Shop admins can manage it; customers,
anonymous visitors, and SEO-only admins cannot.

## Administrator workflow

1. Choose **افزودن دکمه**, enter a descriptive title, and select a platform.
2. Enter its phone number, username, or email. Alternatively, provide a complete
   destination in **نشانی دلخواه**; it overrides the generated platform link.
3. Choose the bottom-left or bottom-right corner and set the display order.
   Lower numbers appear higher in each stack; the ↑/↓ buttons reorder that side.
4. Optionally set tooltip text and the option to open web links in a new tab.
5. Choose an icon or upload a file, enable the button, and save.

An uploaded icon wins over an icon selected from the existing footer library.
The library icon wins over the selected built-in icon. Without an icon selection,
the platform preset is used; unknown platforms get a link icon. Library icons
can also be managed through the existing footer dashboard.

Select **پلتفرم دیگر** to enter a new platform identifier and URL. The database
does not constrain platform names to the preset list. LinkedIn usernames generate
personal `/in/` profile links; use the URL override for a company page or any other
special destination. Generated links are displayed on each dashboard card.

Phone numbers accept Persian/Arabic digits, spaces, hyphens, and parentheses.
International `00` prefixes become `+`. WhatsApp strips `+` and translates Iranian
`09xxxxxxxxx` mobile numbers into `989xxxxxxxxx`. Other international numbers
should include their country code. Phone and SMS links preserve local numbers.

PNG and SVG use the existing category-icon validator (5 MiB maximum). SVG files
must pass its element/attribute allowlist; they are rendered as images, never
injected as HTML. JPEG and WebP use the existing footer image limits (2 MiB,
16,777,216 pixels), with an additional real-format/extension check. Unsupported
formats and invalid content are rejected. Replaced/deleted files are removed only
after the database transaction commits and no button references the file.

Only HTTP(S), `tel`, `sms`, and `mailto` destinations are accepted. Contact schemes
take a single phone number or email address; query parameters on these schemes
are intentionally rejected. Use a complete HTTP(S) share link for prefilled
messages. Credentials, control characters, unsafe schemes, and malformed ports
are rejected. Links opening new tabs receive `noopener noreferrer`; phone, SMS,
and email links hand off directly to the relevant application.

## API

Paths omit trailing slashes, matching the existing dashboard API.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/site-settings/floating-contact-buttons` | Active buttons, ordered by `displayOrder`, then ID |
| GET / POST | `/api/admin/floating-contact-buttons` | List all buttons/platform presets or create a button |
| PATCH / DELETE | `/api/admin/floating-contact-buttons/{id}` | Edit or delete |
| POST | `/api/admin/floating-contact-buttons/{id}/move` | `{ "direction": "up" }` or `"down"` |
| POST / DELETE | `/api/admin/floating-contact-buttons/{id}/icon` | Upload multipart `file` or remove the upload |

The public envelope is `{ "ok": true, "data": { "buttons": [...] } }`.
Each button exposes `id`, `title`, `platform`, final `url`, resolved `icon`,
`iconName`, `tooltipText`, `openInNewTab`, `position`, and `displayOrder`.
Admin DTOs additionally expose the editable inputs, upload/library selection, and
activation state. Validation errors return HTTP 422 with the standard error
envelope and `data.fieldErrors` keyed by the frontend's camelCase field names.

## Rendering and cache

`FloatingContactButtons` is a server component mounted once in the root layout,
under a null Suspense fallback. It fetches only public data and renders nothing
on empty configuration or backend failure. A small client wrapper uses the current
pathname to hide both stacks on `/admin` and every admin subroute. It does not
fetch on client navigation.

The server fetch deliberately shares `footerFetchOptions` and the `footer` cache
tag: replacing or deleting a selected library icon must also refresh contact
buttons. Contact mutations use the existing post-commit revalidation helper and
`FRONTEND_REVALIDATE_URL` / `FRONTEND_REVALIDATE_SECRET` setup. Production has the
same 60-second time-based revalidation fallback; development uses `no-store`.
An already-open storefront layout updates on reload or router refresh, not by
polling. No frontend redeployment is needed. The dashboard refreshes the router
after successful changes; without a webhook, production may need the cache window
and a subsequent reload before showing the update.

Each physical corner has an ordered vertical stack. The buttons use the brand
colors, 48px mobile/52px desktop touch targets, fixed positioning, mobile safe
areas, native tooltips, focus outlines, and reduced-motion support. Long stacks
scroll within the available viewport. `CompareTray` publishes its measured height
through `--compare-tray-h`, keeping the buttons above the comparison controls.

## Migration and verification

`contacts/0001_initial.py` creates `FloatingContactButton`, its active/order index,
and its optional reference to `FooterIcon`. It creates no active/default buttons.
The checkout's environment is `backend/.venv` (some installations use `venv`).

```sh
cd backend
.venv/bin/python manage.py migrate
.venv/bin/python manage.py test contacts footer catalog.test_category_icons --noinput
.venv/bin/python manage.py makemigrations --check --dry-run
```

```sh
cd frontend
node --experimental-strip-types --test tests/*.test.mjs
npm run lint
npx tsc --noEmit
npm run build
```

The contact frontend tests use the existing `node:test` runner and compile the
actual TSX with the already-installed TypeScript compiler. They render React
markup and test links, icons, ordering, route visibility, cache options, failure
handling, and responsive CSS rules. These checks do not replace a browser test of
viewport geometry and keyboard interactions.

Verification for this implementation: 185 backend tests passed (contacts, footer,
category icons); all 12 new frontend tests passed; lint, TypeScript, Django checks,
and the migration consistency check passed. The full frontend suite has 90 passes
and two pre-existing failures in `admin-roles.test.mjs` (developer-route boundaries
and superuser SEO access); neither its tests nor its role logic was changed.

The default Turbopack build could not bind a worker port in the execution sandbox.
A webpack production build succeeded with temporary `useTypeScriptCli: false`,
`webpackBuildWorker: false`, `workerThreads: true`, and `cpus: 1` settings, because
captured child-process stdout was also empty in this environment. The original
`next.config.ts` was restored. A headless Firefox attempt exited before rendering,
so browser-level geometry and interaction verification remains unperformed.

## File inventory

Created backend files: `contacts/__init__.py`, `apps.py`, `models.py`,
`validation.py`, `selectors.py`, `services.py`, `dto.py`, `serializers.py`,
`views_admin.py`, `views_public.py`, `urls.py`, `tests.py`,
`migrations/__init__.py`, `migrations/0001_initial.py`, and this guide.

Created frontend files: `src/app/admin/floating-contact-buttons/page.tsx`,
`src/components/layout/ContactIcon.tsx`, `FloatingContactButtons.tsx`,
`FloatingContactButtonsClient.tsx`, `src/lib/floating-contacts.ts`,
`src/lib/floating-contacts-server.ts`, and `tests/floating-contacts.test.mjs`.

Modified backend files: `config/settings.py` and `config/urls.py` register the app
and API; `footer/selectors.py` and `footer/dto.py` include contact references in
the shared icon library's usage counts.

Modified frontend files: `src/app/layout.tsx`, `src/app/admin/layout.tsx`,
`src/app/globals.css`, and `src/components/product/CompareTray.tsx` integrate the
component, navigation, styling, and comparison clearance.
