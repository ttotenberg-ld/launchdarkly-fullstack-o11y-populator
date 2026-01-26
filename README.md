# LaunchDarkly Observability Demo

A full-stack microservices demo that generates realistic observability data (traces, logs, errors, sessions) for LaunchDarkly's observability platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                                │
│                         http://localhost:3000                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   Dashboard     │  │  Auto-Play      │  │   Manual Demo   │              │
│  │   Metrics       │  │  Simulation     │  │   Controls      │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API Gateway (:5000)                                   │
│                    Routes requests to services                               │
└─────────────────────────────────────────────────────────────────────────────┘
           │              │              │              │
           ▼              ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │  Auth    │   │  User    │   │  Order   │   │  Search  │
    │ :5001    │   │ :5002    │   │ :5003    │   │ :5008    │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
           │              │         │    │              │
           ▼              ▼         │    ▼              ▼
    ┌──────────┐   ┌──────────┐    │  ┌──────────┐   ┌──────────┐
    │Analytics │   │Notific.  │    │  │ Payment  │   │Inventory │
    │ :5007    │   │ :5006    │    │  │ :5004    │   │ :5005    │
    └──────────┘   └──────────┘    │  └──────────┘   └──────────┘
                                   │       │              │
                                   └───────┴──────────────┘
                                           ▼
                                    ┌──────────┐
                                    │Notific.  │
                                    │ :5006    │
                                    └──────────┘
```

## Features

- **9 Flask Microservices**: Realistic service mesh with inter-service communication
- **Distributed Tracing**: End-to-end traces spanning frontend through multiple backend services
- **Error Injection**: Configurable error rates that inject errors deep in trace chains
- **Traffic Simulator**: Headless Python script generating continuous realistic traffic
- **Auto-Play Frontend**: Browser-based simulation with real-time activity feed
- **LaunchDarkly Observability**: Full integration with traces, logs, errors, and session replay

## Quick Start

### Prerequisites

- Docker and Docker Compose
- LaunchDarkly account with Observability enabled

### Setup

1. **Clone and configure:**

```bash
cd sor
cp .env.example .env
```

2. **Edit `.env` with your LaunchDarkly credentials:**

```bash
LD_SDK_KEY=sdk-xxxxx          # Server-side SDK key
VITE_LD_CLIENT_SIDE_ID=xxxxx  # Client-side ID
```

3. **Start all services:**

```bash
docker-compose up --build
```

4. **Access the demo:**

- Frontend: http://localhost:3000
- API Gateway: http://localhost:5000

## Services

| Service | Port | Description |
|---------|------|-------------|
| `api-gateway` | 5000 | Routes requests, auth validation |
| `auth-service` | 5001 | Login, token validation, sessions |
| `user-service` | 5002 | User profiles, preferences |
| `order-service` | 5003 | Order processing, checkout flow |
| `payment-service` | 5004 | Payment processing (error-prone) |
| `inventory-service` | 5005 | Stock management, reservations |
| `notification-service` | 5006 | Email/push notifications |
| `analytics-service` | 5007 | Event tracking |
| `search-service` | 5008 | Product search |

## Generating Traffic

### Option 1: Frontend Auto-Play

1. Open http://localhost:3000
2. Click the "Auto-play" toggle in the header
3. Adjust the rate slider to control requests per minute

### Option 2: Headless Simulator

The simulator container runs automatically with Docker Compose:

```bash
# View simulator logs
docker-compose logs -f simulator

# Adjust rate via environment variable
REQUESTS_PER_MINUTE=60 docker-compose up simulator
```

### Option 3: Manual Testing

Use the demo buttons in the frontend to manually trigger:
- Error scenarios (frontend + backend)
- Log messages at different severity levels
- Distributed traces through the service mesh

## Traffic Scenarios

The simulator and auto-play feature run these weighted scenarios:

| Scenario | Weight | Description |
|----------|--------|-------------|
| Browse Products | 35% | List and view products |
| User Login | 20% | Authentication flow |
| Checkout Flow | 15% | Full checkout with payment |
| Search Products | 15% | Search and filter |
| Update Profile | 10% | Profile preferences |
| View Dashboard | 5% | Dashboard metrics |

## Error Injection

Errors are injected based on configurable rates per service:

- **Payment Service**: 6% payment declined, 3% gateway timeout
- **Inventory Service**: 8% out of stock
- **Auth Service**: 5% invalid token
- **API Gateway**: 2% rate limit exceeded

This creates realistic error scenarios that appear deep in trace chains.

## User Personas

Sessions use LaunchDarkly-punny email addresses:

- luna@staylightly.io
- lance@darklaunchly.com
- darcy@lunchdarkly.net
- larry@launchdorkly.io
- lydia@dimlylaunch.com
- drake@launchbrightly.io
- dawn@toggledarkly.com
- felix@flaglaunchly.io
- sage@rolldarkly.net
- nova@launchsoftly.io

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LD_SDK_KEY` | - | LaunchDarkly server-side SDK key |
| `VITE_LD_CLIENT_SIDE_ID` | - | LaunchDarkly client-side ID |
| `ENVIRONMENT` | development | Environment name |
| `REQUESTS_PER_MINUTE` | 30 | Simulator request rate |
| `ERROR_SESSION_RATE` | 0.15 | Percentage of sessions with errors |

## Development

### Running Locally (without Docker)

**Backend services:**

```bash
cd backend
pip install -r requirements.txt

# Start each service (in separate terminals)
cd services/api-gateway && python app.py
cd services/auth-service && python app.py
# ... etc
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**Simulator:**

```bash
cd simulator
pip install -r requirements.txt
python traffic_generator.py
```

## Observability in LaunchDarkly

After running for a few minutes, you should see in your LaunchDarkly dashboard:

1. **Traces**: Distributed traces showing request flow through services
2. **Errors**: Errors with source attribution (frontend/backend)
3. **Logs**: Structured logs at different severity levels
4. **Sessions**: User sessions with replay capability

### Filtering Tips

- Filter by `source: frontend` or `source: backend`
- Filter by `service: payment-service` to see payment errors
- Look for traces with errors to see where failures occur in the chain

## Troubleshooting

### Services not connecting

```bash
# Check if all containers are running
docker-compose ps

# View logs for a specific service
docker-compose logs api-gateway
```

### No data in LaunchDarkly

1. Verify your SDK keys are correct in `.env`
2. Check service logs for connection errors
3. Ensure your LaunchDarkly project has Observability enabled

### Frontend not loading

```bash
# Rebuild the frontend
docker-compose build frontend
docker-compose up -d frontend
```

## License

MIT
