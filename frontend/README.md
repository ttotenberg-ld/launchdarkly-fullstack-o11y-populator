# Frontend

React + Vite storefront that drives the demo. Renders the UI real users and the Playwright simulator interact with — and emits client-side LaunchDarkly flag evaluations, Observability telemetry, and Session Replay. For cross-repo context (flags, contexts, signal inventory) read [`../AGENTS.md`](../AGENTS.md).

## Stack

- **React 18** + **Vite 6** (ES modules, `@vitejs/plugin-react`)
- **React Router v6** for page routing
- **LaunchDarkly client SDK** (`launchdarkly-js-client-sdk` + `launchdarkly-react-client-sdk`)
- **LD Observability plugin** (`@launchdarkly/observability`) + **LD Session Replay** (`@launchdarkly/session-replay`)
- **Nginx** serving the `vite build` output in production (container port 80 → host 3000)

## Layout

```
frontend/
├── src/
│   ├── main.jsx               # LD SDK init + Observability + SessionReplay plugins
│   ├── App.jsx                # root, evaluates migrate-warehouse-api on mount (for feature events)
│   ├── Router.jsx             # route table
│   ├── context/CartContext.jsx# cart state, persisted in localStorage (`ld-store-cart`)
│   ├── services/api.js        # single fetch wrapper; sends X-User-* headers on every call
│   ├── pages/                 # Home, Products, ProductDetail, Cart, Checkout, Account, …
│   ├── components/
│   │   ├── layout/            # Navbar, Footer, PromoBanner (promo-banner flag)
│   │   ├── products/          # ProductCard (product-card-layout flag)
│   │   ├── cart/              # CartItem, CartSummary
│   │   ├── checkout/          # ShippingForm, PaymentForm, OrderSummary
│   │   ├── ChatWidget.jsx     # talks to chat-service (LD AI Config)
│   │   └── FeedbackWidget.jsx # posts feedback with o11y_session_id → Session Replay jump
│   └── utils/                 # telemetry helpers, error-injection sandbox
├── public/
├── Dockerfile                 # two-stage Node build → Nginx runtime
├── nginx.conf
├── vite.config.js
├── package.json
└── .env.example
```

## LD SDK boot sequence

Read `src/main.jsx` top to bottom — the ordering matters and the comments explain why.

Summary:

1. **Session-replay privacy is fetched via the client-side eval REST endpoint, BEFORE SDK init.** `SessionReplay`'s `privacySetting` is constructor-only — flipping the `session-replay-privacy` flag mid-session has no effect. The privacy level takes effect on the next page load.
2. **Initial user context is assembled from `window.__LD_USER__`** if the simulator injected one, otherwise a random key. The simulator also sets `window.__BROWSER_PROFILE__` so the initial evaluation already carries browser profile + form factor.
3. **`asyncWithLDProvider` resolves when streaming flag data arrives.** The app renders nothing until then — this is fine for the demo and avoids flash-of-default-variation.
4. Observability plugin is configured with `tracingOrigins: true` + `recordHeadersAndBody: true` — full network detail in the LD dashboard.
5. `version` on the Observability plugin is baked at **build time** from `VITE_SERVICE_VERSION` (see the Dockerfile `ARG`), falling back to `'dev'` for `vite dev`.

## Client-side flag evaluations

Via `useFlags()` from `launchdarkly-react-client-sdk`. The React SDK emits a `feature` event the first time a flag is read in render, which is why `App.jsx` evaluates `migrate-warehouse-api` on mount even though the client doesn't *use* its value (the server is authoritative) — reading it registers a client-side evaluation for dashboards.

| Flag | Used in | Effect |
|---|---|---|
| `product-card-layout` | `pages/Products.jsx:15`, `pages/Checkout.jsx:20`, `components/products/ProductCard.jsx:20` | `standard` / `minimal` / `detailed` — ProductCard variant. Tagged on funnel metrics as `layout_variant`. |
| `promo-banner` | `components/layout/PromoBanner.jsx:17`, `pages/Checkout.jsx:21` | `none` / `free-shipping-50` / `percent-off` / `urgency`. Tagged on checkout metrics as `promo_variant`. |
| `session-replay-privacy` | `src/main.jsx:40` (pre-init REST fetch) | `none` / `default` / `strict` — SessionReplay privacy. Constructor-only. |
| `migrate-warehouse-api` | `src/App.jsx:18` (read for feature-event emission, value unused) | Server-authoritative in `inventory-service`. |

## API layer

All HTTP calls go through `src/services/api.js`. A single fetch wrapper:

- Prepends `VITE_API_URL` (api-gateway)
- Sets `X-User-*` headers from the LD context — **source of truth for user identity across services**
- Propagates Observability trace context via browser fetch instrumentation (automatic)
- Parses JSON + throws on non-2xx

If you add a new user attribute, thread it through the chain: simulator → `window.__LD_USER__` → `main.jsx` initial context → `api.js` headers → backend `_user_from_headers` → each service's context builder. Missing a link silently drops the attribute from server-side eval.

## Observability + Session Replay

Every page mutation worth tracking calls `LDObserve.recordCount` / `recordHistogram` / `recordLog` / `recordError`. The full signal inventory lives in [`../SIGNALS.md`](../SIGNALS.md).

`FeedbackWidget.jsx` attaches `sessionSecureID` to feedback events as `o11y_session_id` so dashboards can jump from feedback → the exact Session Replay.

## Running it

Production flow is `docker compose up -d frontend` from the repo root. That produces the nginx-served build on `:3000`.

Fast iteration against a running backend:

```bash
cd frontend
npm install
cp .env.example .env     # fill VITE_LD_CLIENT_SIDE_ID, point VITE_API_URL at the gateway
npm run dev              # Vite dev server on :5173 with HMR
```

Note: `VITE_SERVICE_VERSION` is only set by the Dockerfile `ARG`. Running `npm run dev` gives you `'dev'` as the Observability plugin version — intentional, so local dev traffic doesn't pollute versioned dashboards.

## Build contract

The Dockerfile takes three `ARG`s, all plumbed through `docker-compose.yml`:

- `VITE_LD_CLIENT_SIDE_ID` — from `.env`
- `VITE_API_URL` — gateway URL
- `VITE_SERVICE_VERSION` — from the root `.env`, the single source of truth for versioning

Bumping `SERVICE_VERSION` in the root `.env` does **not** rebuild the frontend on its own — run `docker compose up -d --build frontend` or the version tagged in LD dashboards will drift from the backend.

## Common frontend pitfalls

- **Constructor-only SessionReplay privacy.** Changing `session-replay-privacy` mid-session has no effect. Reload.
- **Cart state lives in localStorage** (`ld-store-cart`). `Checkout.jsx` redirects to `/cart` if `cartItems.length === 0`. Empty cart = no checkout = no `payment-processor-migration` eval.
- **Error Boundary** in `components/infrastructure/` catches render-phase errors and calls `LDObserve.recordError`. Async errors still need try/catch.
- **Nginx config** in `nginx.conf` must pass through `/api/*` — both for API calls and so the LD SDK's network instrumentation sees a same-origin response. Changing Nginx routing is usually the root cause if traces suddenly stop propagating.
- **CSP headers** in `index.html` allow LD domains. If you see console errors about blocked connections to `*.launchdarkly.com` after changing the meta tag, this is why.
