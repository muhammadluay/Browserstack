# testathon.live — URL and Feature Map

Last verified: 2025-09-20 (UTC)

This document summarizes the publicly discoverable pages, APIs, and behaviors of https://testathon.live/ based on live crawling and static asset inspection. The site is a Next.js (static export) front‑end titled “StackDemo” served by nginx.

See also: `helpful/todo.md` — hands-on validation checklist derived from this map.

## Overview

- Server: nginx/1.24.0 (Ubuntu)
- App: Next.js (static export), title: StackDemo
- Robots/sitemap: `/robots.txt` and `/sitemap.xml` return 404
- Assets: `/_next/static/...` hashed JS/CSS chunks; product images under `/_next/static/images/...`
- Favicon: `/favicon.svg`

## Pages (GET)

- `/` (200)
  - Home/catalog shell; product UI loads via JS.
- `/signin` (200)
  - Sign‑in page. On success, stores `sessionStorage.username`.
- `/offers` (200)
  - Promotional offers (requires login). Uses browser geolocation and calls `/api/offers` with `userName`, rounded `latitude`, `longitude`. If not logged in, redirects to `/signin?offers=true`.
- `/orders` (200)
  - Order history (requires login). Calls `/api/orders?userName=...` and also merges with `sessionStorage.userOrders`. If not logged in, redirects to `/signin?orders=true`.
- `/checkout` (200)
  - Checkout flow (requires items in cart and login). Form submit posts to `/api/checkout` with `{ userName }`, clears cart, persists an order to `sessionStorage.userOrders`, then redirects to `/confirmation`. If not logged in, redirects to `/signin?checkout=true`; if cart empty, redirects to `/`.
- `/confirmation` (200)
  - Order confirmation page. Reads `sessionStorage.confirmationProducts` and `sessionStorage.confirmationTotal`. Includes client‑side PDF/table libs (likely for receipt rendering).
- `/favourites` (200)
  - Favourites (requires login). Redirects to `/signin?favourites=true` if not logged in; content from client state/session.
- `/swagger` (200)
  - “BrowserStack Demo API” Swagger UI page (client‑side rendered). No public `/openapi.json` or `/swagger.json`; the UI is bundled.

Discovered via Next.js build manifest (`/_next/static/<buildId>/_buildManifest.js`).

## API Endpoints (observed)

- `GET /api/products` (200)
  - Returns product catalog JSON.
  - Fields per product include: `id`, `title`, `description`, `price`, `currencyFormat`, `currencyId`, `sku` (image key), `availableSizes` (brand), `installments`, `isFav`.

- `POST /api/signin`
  - Validates username (and possibly password). On invalid username returns 422 with `{ "errorMessage": "Invalid Username" }`.
  - Example (invalid):
    - Request: `POST /api/signin` with `{ "username": "demouser", "password": "secret" }`
    - Response: 422 `{ "errorMessage": "Invalid Username" }`

- `GET /api/orders?userName=<name>`
  - Returns user orders; 404 with `{ "message": "No orders found" }` when none exist.

- `GET /api/offers?userName=<name>&latitude=<int>&longitude=<int>`
  - Returns offers based on coarse geolocation; 404 with `{ "cityName": "" }` when none match.

- `POST /api/checkout`
  - Currently responds with 422 for observed requests (even when `userName` is provided). A `GET` to this path also returns 422.
  - The front‑end handles checkout client‑side: on submit it posts to `/api/checkout`, clears the cart, persists an order to `sessionStorage.userOrders`, then redirects to `/confirmation`.

## Client Behavior Notes

- Auth/session: Uses `sessionStorage.username` as login flag for protected pages.
- Orders: On successful checkout, the client appends a synthesized order into `sessionStorage.userOrders` and clears cart/total state.
- Confirmation: Uses `sessionStorage.confirmationProducts` and `sessionStorage.confirmationTotal` to render the receipt.
- Offers: Requires `navigator.geolocation`; passes rounded latitude/longitude to `/api/offers`.

## Quick Status Snapshot

Pages:

```
/              200
/signin        200
/offers        200
/orders        200
/checkout      200
/confirmation  200
/favourites    200
/swagger       200
```

APIs:

```
GET  /api/products                           200
GET  /api/orders?userName=<name>             404 when none
GET  /api/offers?userName=<n>&lat=..&lon=..  404 when none
POST /api/signin                              422 on invalid username
GET  /api/checkout                            422
POST /api/checkout                            200 (empty JSON)
```

Not present:

```
GET /robots.txt      404
GET /sitemap.xml     404
GET /openapi.json    404
GET /swagger.json    404
```

## Reproduce Locally (examples)

```
curl -s https://testathon.live/_next/static/$(curl -s https://testathon.live/ | sed -n 's/.*"\/_next\/static\/(.*)\/_buildManifest.js".*/\1/p')/_buildManifest.js

curl -s https://testathon.live/api/products | jq .products[0]

curl -s -i -X POST https://testathon.live/api/checkout \
  -H 'Content-Type: application/json' \
  --data '{"userName":"demouser"}'
```

## Notes

- Observations reflect the live site on 2025‑09‑20 and may change.
- Swagger UI renders at `/swagger`, but the OpenAPI document is not publicly exposed under common paths.
