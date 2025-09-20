# testathon.live — QA Recon Report and Missing Tests

Last scanned: 2025-09-20 10:06 UTC

## Executive Summary
- Site serves a BrowserStack demo–style e‑commerce app (Next.js) via Nginx on Ubuntu over HTTPS.
- Core routes discovered: `/`, `/offers`, `/signin`, `/orders`, `/checkout`, `/confirmation`, `/swagger`.
- API endpoints respond on same origin: `/api/products`, `/api/orders`, `/api/offers`, `/api/checkout`, `/api/signin` (minimal/no‑auth behavior).
- Security hardening is weak: no CSP/HSTS/XFO/XCTO/etc; `www` subdomain not covered by certificate and returns 404.
- SEO is minimal: no robots.txt/sitemap.xml/canonical/meta description/OG/Twitter tags.
- Initial payload is JS‑heavy but reasonable for a SPA (~577 KB JS + ~32 KB CSS before images). HTML is skeletal (client‑rendered content).

## Tech/Infra Observations
- Server: `nginx/1.24.0 (Ubuntu)`.
- App: Next.js (static export variant); `X-Powered-By: Next.js`.
- TLS/URLs:
  - `http://testathon.live` → 301 to `https://testathon.live` (OK).
  - `https://www.testathon.live` → certificate mismatch (CN/SAN does not include `www`).
  - `http://www.testathon.live` → HTTP 404.

## Routes and Behavior
- `/` (Home): Head title `StackDemo`. Renders content client‑side via JS chunks.
- `/offers`: Requires session user; requests geolocation; calls `/api/offers?userName=...&latitude=...&longitude=...`.
- `/signin`: Client login UI; storage appears to rely on session storage; server accepts `/api/signin` POST returning `{}`.
- `/orders`: Requires session user; merges client `userOrders` (session) with `/api/orders?userName=...` results; displays list or “No orders found”.
- `/checkout`: Requires cart + session user; POSTs `/api/checkout { userName }`; then fills local session `userOrders` and redirects to `/confirmation`.
- `/confirmation`: Shows client‑side confirmation based on session values.
- `/swagger`: Loads Swagger UI (page title: “BrowserStack Demo API”). Spec URL embedded in JS (not directly exposed at `/swagger.json`).

## API Inventory (sample calls)
- `GET /api/products` → 200 JSON list of 25 devices with fields: `id,title,description,price,sku,availableSizes,isFav,…` (observed Content-Length ~5120 bytes).
- `GET /api/orders?userName=<name>` → 404 `{"message":"No orders found"}` when empty.
- `GET /api/offers?userName=<name>&latitude=<int>&longitude=<int>` → 404 `{"cityName":""}` when no offers.
- `POST /api/checkout` JSON `{"userName":"<name>"}` → 200 `{}`.
- `POST /api/signin` JSON `{"userName":"<name>","password":"<pwd>"}` → 200 `{}` (no observable token/cookie in response).

Notes:
- API appears stateless and permissive; client relies on sessionStorage for most “state” (cart/orders/confirmation).
- No auth cookies or headers observed; no CSRF protections evident.

## Performance Snapshot (unauthenticated homepage)
- HTML: ~4.2 KB; CSS: ~32.7 KB; JS: ~590.4 KB (sum of `Content-Length` across `<script src>` on `/`).
- Example image asset size: `/ _next/static/images/GooglePixel3-device-info-*.png` ~15.1 KB.
- No HTTP/2 push (expected). Uses standard Next.js chunking; many small to medium chunks.

## Security Headers (missing)
- Absent on sampled routes: `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`.
- Cookies not set for auth; session state in Web Storage (susceptible to XSS data theft; CSP missing increases risk).

## SEO/Indexing
- `robots.txt`: 404
- `sitemap.xml`: 404
- Meta tags: No `meta description`, Open Graph, or Twitter Card tags on `/`.
- No page‑level canonical URLs observed.

## Accessibility (surface checks)
- Client renders most content; without JS, page is empty aside from `<footer>`. No SSR content → degraded experience for assistive tech with JS disabled.
- Offers page uses images with `alt` set (observed in code for offers), but full audit needed for focus states, landmark regions, ARIA roles, color contrast, and keyboard traps.

## Notable Issues/Risks
- Security misconfigurations:
  - No HSTS; `www` subdomain TLS invalid → user trust/mixed navigation issues.
  - No CSP/XFO/XCTO/etc. → elevated XSS/clickjacking risks.
- Authentication model:
  - Server accepts signin/checkout with `{}` responses; no server‑validated identity tokens; client trust of sessionStorage.
  - Lack of CSRF protections (though no cookies used); but POSTs should still validate origin/intents.
- Observability/SLOs unknown (no headers for tracing; no error correlation surfaced to client).

---

## Missing Test Coverage — Senior QA Checklist (Crucial Tests)

1) End‑to‑End Core Flows
- Guest → Sign in → Filter/browse products → Add to cart → Checkout → Confirmation → Orders history visibility.
- Repeat checkout with existing `userOrders`; verify deduplication/merge logic between `/api/orders` and session `userOrders`.
- Offers flow with geolocation allowed/denied/unavailable; verify error messages and fallback.

2) Negative and Edge Cases
- API failures (5xx/timeout) for: products, orders, offers, checkout, signin; ensure resilient UI with retries/toasts and no stuck states.
- Empty states: no products, no orders, no offers; validate copy and accessibility.
- Malformed inputs (e.g., non‑int lat/long; unexpected `userName` characters; large payloads; duplicate items in cart).

3) Authentication/Session
- Sign‑in variations: valid/invalid creds, blank fields, rate‑limit/lockout behavior (currently server returns `{}` always → bug/placeholder?).
- SessionStorage clearing across tabs and after logout; ensure protected routes redirect reliably.
- Direct URL access to `/orders`, `/checkout`, `/offers` without session; verify redirect to `/signin` with query flags.

4) API Contract/Schema
- Contract tests for `/api/products`, `/api/orders`, `/api/offers`, `/api/checkout`, `/api/signin`:
  - Required fields, types, status codes (200/4xx/5xx), error bodies.
  - Idempotency/safety: repeated `/api/checkout` calls; ensure no inconsistent state.

5) Security
- HTTP headers: verify and enforce HSTS, CSP (restrict script/img/connect sources), XFO `DENY`/`SAMEORIGIN`, XCTO `nosniff`, Referrer‑Policy, Permissions‑Policy.
- XSS probes across any rendered user data; storage poisoning via sessionStorage values used in DOM.
- Clickjacking: ensure frames blocked on sensitive pages.
- TLS/Domain hygiene: `www.testathon.live` certificate and routing.
- CSRF posture: even without cookies, validate intent (e.g., origin headers) for POST endpoints.

6) Accessibility (WCAG 2.1 AA)
- Keyboard‑only navigation for all flows (focus order, visible focus, escape modals).
- Landmarks (`header/main/footer/nav`), ARIA roles, labels for inputs and buttons.
- Color contrast for text/buttons; zoom/responsive up to 400%.
- Screen reader announcements on route changes (SPA) and toast/validation messages.

7) Performance and Resilience
- Synthetic and RUM baselines: LCP/INP/CLS on key routes (home, offers, cart/checkout).
- Slow 3G/CPU throttling: ensure skeletons/spinners; avoid layout shifts.
- Caching: verify static assets caching (ETag/Last‑Modified present; consider far‑future cache with hashed filenames).
- Payload budgets: enforce JS ≤ ~300–400 KB for initial route where possible; code‑split opportunities.

8) Cross‑Browser/Device Matrix
- Chrome/Firefox/Safari/Edge latest; iOS Safari; Android Chrome.
- Mobile: offers geolocation permissions, keyboard overlays, viewport scaling.
- High DPI and low‑end devices (CPU throttled) — check responsiveness/hangs.

9) SEO
- robots.txt and sitemap.xml presence and correctness; disallow non‑prod/staging.
- Meta description, canonical URLs, OG/Twitter cards; SSR of critical content or fallback meta for crawlers.

10) Observability & Error Handling
- Frontend: network error logging, user‑safe messages (no stack traces), tracing IDs.
- Backend: request IDs, structured logs, SLO/alerts for API health.

## Quick Repro/Validation Snippets (cURL)
```bash
# Products
curl -s https://testathon.live/api/products | jq '.products | length'

# Orders (no orders case)
curl -s 'https://testathon.live/api/orders?userName=demouser'

# Offers (without valid geo)
curl -s 'https://testathon.live/api/offers?userName=demouser&latitude=10&longitude=20'

# Checkout (stateless placeholder)
curl -s -X POST https://testathon.live/api/checkout \
  -H 'Content-Type: application/json' \
  --data '{"userName":"demouser"}'

# Sign in (placeholder)
curl -s -X POST https://testathon.live/api/signin \
  -H 'Content-Type: application/json' \
  --data '{"userName":"demouser","password":"testingisfun99"}'
```

## Recommendations (Prioritized)
1) Fix `www` domain DNS/TLS; add HSTS (includeSubDomains + preload) after validating.
2) Add CSP, XFO, XCTO, Referrer‑Policy, Permissions‑Policy; audit inline scripts for CSP.
3) Implement real auth on `/api/signin` with proper responses, tokens/cookies, and CSRF mitigations if cookies are used.
4) Improve SEO (robots/sitemap/meta/canonical) and basic SSR for critical content or prerender meaningful HTML.
5) Add robust error states and API retry/backoff; unify error UX.
6) Establish performance budgets and monitoring for LCP/INP/CLS; reduce initial JS where possible.
7) Build out automated test suites covering the “Missing Test Coverage” above (E2E via Playwright; API via Postman/Newman or Pact; a11y via axe/lighthouse; headers via ZAP/OWASP baseline).

