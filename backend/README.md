# Backend services

Ten Flask microservices behind an API gateway, plus a shared library. Each service is independently Dockerised and runs in `docker-compose.yml` at the repo root. For the system-wide picture (flags, contexts, service topology) read [`../AGENTS.md`](../AGENTS.md) — this file is the backend-local view.

## Layout

```
backend/
├── services/
│   ├── api-gateway/         # :5000 (host 5050) — fans requests out to the others
│   ├── auth-service/        # :5001
│   ├── user-service/        # :5002 — userdb
│   ├── order-service/       # :5003 — orderdb, evaluates payment-processor-migration (log-only)
│   ├── payment-service/     # :5004 — paymentdb, evaluates payment-processor-migration (authoritative)
│   ├── inventory-service/   # :5005 — inventorydb, evaluates migrate-warehouse-api (error injection)
│   ├── notification-service/# :5006
│   ├── analytics-service/   # :5007 — retention reaper
│   ├── search-service/      # :5008 — reads inventorydb cross-service (deliberate)
│   └── chat-service/        # :5009 — chatdb, LD AI Config + Ollama
├── shared/
│   ├── observability.py     # LD SDK + OTel bootstrap (used by every service)
│   ├── db.py                # SQLAlchemy engine factory, health-check wait loop
│   ├── users.py             # X-User-* header parsing → multi-context builder helpers
│   ├── service_names.py     # canonical service-name constants
│   └── reaper.py            # background retention job (analytics-service)
└── requirements.txt         # one lockfile shared across all services
```

Each service is a single `app.py` — intentionally flat. This is a demo populator, not production code.

## Service startup contract

Every service follows the same init order. Deviating breaks distributed tracing or double-instruments the app — see the docstrings in `shared/observability.py`.

```python
from shared.observability import create_ld_client, setup_flask_instrumentation

app = Flask(__name__)
ld_client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)  # 1. LD SDK + Observability plugin
setup_flask_instrumentation(app)                              # 2. Flask + requests instrumentation
# (SQLAlchemyInstrumentor is wired per-service in the services that touch DBs)
```

The LD Observability plugin sets up the OTel tracer provider. Flask instrumentation has to come after it, and W3C propagation is set inside `setup_flask_instrumentation` for the same reason (see the in-file comment).

## Multi-context flag evaluation

Services that evaluate flags build a **multi-context** from three kinds:

- `user` — end-user identity from `X-User-*` request headers (set by the gateway from the frontend)
- `request` — ephemeral anonymous context with endpoint/method/timestamp
- `service` — stable service identity, key = service name

The `_build_user_context()` function is intentionally duplicated in each flag-evaluating service (`inventory-service`, `payment-service`, `order-service`) so each service owns its own context shape. Non-evaluating services use `_user_from_headers()` to hydrate a user dict for logs/spans only.

Header list is centralised in `USER_HEADERS`:

```
X-User-Key, X-User-Name, X-User-Email, X-User-Plan,
X-User-Role, X-User-Metro, X-User-Country
```

Adding a new user field? Thread it through: simulator → frontend → gateway → each service's context builder. Missing any link silently drops it from server-side eval.

## Distributed tracing

W3C `traceparent` / `tracestate` is propagated automatically via the instrumented `requests` library. Every service calling downstream should use `get_trace_headers()` (defined locally in each service) to inject the current trace context when making HTTP calls to another service.

SQLAlchemy is instrumented per-service in services that hit Postgres. Every DB call produces a child span nested under the HTTP span.

## Flags evaluated in the backend

| Flag | Where | Behaviour |
|---|---|---|
| `migrate-warehouse-api` | `inventory-service/app.py:151` (`get_warehouse_api_version`) | v1 = clean (no injection), v2 = ~93% composite errors, v3 = clean. Full scenario table in the file. |
| `payment-processor-migration` | `payment-service/app.py:135` (`get_processor_version`) | **Authoritative**. v2 routes DB pathologies (slow_query, seq_scan_regression, pool_hold, rollback). v1/v3 clean. |
| `payment-processor-migration` | `order-service/app.py` `/checkout` | Logged + span-tagged only — **not** behaviour-driving. Used to widen the guarded-rollout sample volume. |

AI Config `support-chatbot` is evaluated in `chat-service/app.py:325` — see `LD_TO_OLLAMA_PARAMS` for the LD-to-Ollama parameter name mapping.

## Database seeding

Postgres runs from `../postgres/initdb/*.sql` on every `docker compose up`. There's **no volume mount** — by design, so every teammate starts from identical seed data. Databases: `appmeta`, `userdb`, `orderdb`, `paymentdb`, `inventorydb`, `chatdb`.

`shared/db.py` provides a connection-retry wait loop used at service boot.

## Running locally

All nine services normally run via `docker compose up -d` from the repo root — that's the supported path. If you need to run one service on the host for fast iteration:

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in LD_SDK_KEY
export SERVICE_NAME=order-service FLASK_PORT=5003
python -m services.order-service.app
```

Point the gateway at your host-bound service with `docker compose up -d --scale order-service=0` and an env override. Honestly this is rarely worth it — rebuild times are 5-10s.

## Adding a new service

1. Create `services/<name>-service/app.py` following the startup contract above.
2. Create `services/<name>-service/Dockerfile` — copy an existing one. Must include `ENV PYTHONUNBUFFERED=1` or `docker compose logs` will lag.
3. Add the service to `docker-compose.yml` at the repo root.
4. Add a route to `api-gateway/app.py` if it should be externally reachable.
5. If it evaluates flags, copy the `_build_user_context()` pattern from an existing service.

## Shared module expectations

- `observability.py::create_ld_client` — call **before** any Flask setup.
- `observability.py::setup_flask_instrumentation` — call **after** `create_ld_client`.
- `observability.py::get_common_attributes` — always include when calling `record_log` / `record_exception` / `record_count` / `record_histogram`.
- `users.py` — header constants and user-context helpers.
- `service_names.py` — use the constants, don't hardcode service-name strings.

## Common backend pitfalls

- **LD SDK init ordering** — see the startup contract section. Reverse it and traces fragment.
- **Double instrumentation** — `ObservabilityConfig(disabled_instrumentations=['flask', 'requests'])` is set in `create_observability_config()` specifically so the LD plugin doesn't double-instrument what we instrument explicitly. Don't remove it.
- **`record_log` ships via OTLP, not stdout** — don't expect to see log lines via `docker compose logs` unless they also go through `print`/`app.logger`. Check the LD dashboard.
- **Postgres healthcheck DB name** — `pg_isready` defaults DB name to the username, which doesn't exist here. `docker-compose.yml` passes `-d appmeta` explicitly.
