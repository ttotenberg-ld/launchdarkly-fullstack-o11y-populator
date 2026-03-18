# LaunchDarkly Observability Demo

A full-stack microservices demo that generates realistic observability data (traces, logs, errors, sessions) for LaunchDarkly's observability platform. Includes an AI support chatbot powered by local LLMs via Ollama, controlled by LaunchDarkly AI Configs.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React)                               │
│                         http://localhost:3000                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │  Products   │  │   Checkout   │  │ Chat Widget  │      │
│  │  Metrics     │  │  & Search   │  │   Flow       │  │ (AI Support) │      │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API Gateway (:5050)                                   │
│                    Routes requests to services                               │
└─────────────────────────────────────────────────────────────────────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
  │  Auth  │ │  User  │ │ Order  │ │ Search │ │  Chat  │
  │ :5001  │ │ :5002  │ │ :5003  │ │ :5008  │ │ :5009  │
  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
       │          │       │    │        │          │
       ▼          ▼       │    ▼        ▼          ▼
 ┌──────────┐ ┌────────┐ │ ┌────────┐ ┌────────┐ ┌────────┐
 │Analytics │ │Notific.│ │ │Payment │ │Invent. │ │ Ollama │
 │  :5007   │ │ :5006  │ │ │ :5004  │ │ :5005  │ │:11434  │
 └──────────┘ └────────┘ │ └────────┘ └────────┘ └────────┘
                          └──────┘
```

## Features

- **10 Flask Microservices**: Realistic service mesh with inter-service communication
- **AI Support Chatbot**: LLM-powered chat using Ollama (Gemma 3 1B / DeepSeek R1 1.5B), controlled by LaunchDarkly AI Configs
- **Distributed Tracing**: End-to-end traces spanning frontend through multiple backend services
- **Error Injection**: Configurable error rates that inject errors deep in trace chains
- **Traffic Simulator**: Playwright-driven browser sessions with human-like behavior (~60s each)
- **LaunchDarkly Observability**: Full integration with traces, logs, errors, and session replay
- **AI Metrics**: Token usage, latency, success/error rates, and user feedback (thumbs up/down) tracked via LD AI SDK

## Quick Start

### Prerequisites

- Docker and Docker Compose
- LaunchDarkly account with Observability enabled

### Setup

1. **Clone and configure:**

```bash
cp .env.example .env
```

2. **Edit `.env` with your LaunchDarkly credentials:**

```bash
LD_SDK_KEY=sdk-xxxxx          # Server-side SDK key
VITE_LD_CLIENT_SIDE_ID=xxxxx  # Client-side ID
```

3. **Start all services:**

```bash
# Without AI chat (lightest, recommended for getting started)
docker compose up -d --build

# With local LLM (Docker-based Ollama, CPU-only on Mac)
docker compose --profile local-models up -d --build

# With native Ollama (GPU-accelerated, fastest on Mac)
# Set OLLAMA_URL=http://host.docker.internal:11434 in .env first
docker compose up -d --build
```

4. **Access the demo:**

- Frontend: http://localhost:3000
- API Gateway: http://localhost:5050

## AI Chat Modes

The AI support chatbot has three deployment modes, controlled by `.env`:

| Mode | `CHAT_ENABLED` | `OLLAMA_URL` | Command | Notes |
|------|----------------|--------------|---------|-------|
| **No LLM** | `false` | (any) | `docker compose up -d --build` | Chat returns "down for maintenance". Lightest on resources. |
| **Local LLM** | `true` | `http://ollama:11434` | `docker compose --profile local-models up -d --build` | Ollama runs in Docker. CPU-only on Mac (slow, ~30s/response). |
| **Native/Remote LLM** | `true` | `http://host.docker.internal:11434` | `docker compose up -d --build` | Points at native Ollama or remote server. GPU-accelerated on Mac (~1-3s). |

### Native Ollama Setup (recommended for Mac)

```bash
brew install ollama
ollama serve &
ollama pull gemma3:1b
ollama pull deepseek-r1:1.5b
```

Then set in `.env`:
```bash
CHAT_ENABLED=true
OLLAMA_URL=http://host.docker.internal:11434
```

### LaunchDarkly AI Config Setup

Create an AI Config named `support-chatbot` with two variations:

**Variation 1 — Gemma 3 1B:**
```json
{
  "model": { "name": "gemma3:1b" },
  "messages": [{ "role": "system", "content": "You are a helpful customer support agent..." }],
  "parameters": { "temperature": 0.7, "max_tokens": 256, "top_p": 0.9 }
}
```

**Variation 2 — DeepSeek R1 1.5B:**
```json
{
  "model": { "name": "deepseek-r1:1.5b" },
  "messages": [{ "role": "system", "content": "You are a helpful customer support agent..." }],
  "parameters": { "temperature": 0.6, "max_tokens": 512, "top_p": 0.95, "top_k": 40 }
}
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `api-gateway` | 5050 | Routes requests, auth validation |
| `auth-service` | 5001 | Login, token validation, sessions |
| `user-service` | 5002 | User profiles, preferences |
| `order-service` | 5003 | Order processing, checkout flow |
| `payment-service` | 5004 | Payment processing (error-prone) |
| `inventory-service` | 5005 | Stock management, reservations |
| `notification-service` | 5006 | Email/push notifications |
| `analytics-service` | 5007 | Event tracking |
| `search-service` | 5008 | Product search |
| `chat-service` | 5009 | AI support chatbot (Ollama + LD AI Configs) |

## Traffic Simulator

The simulator runs Playwright browser sessions that behave like real users — browsing products, searching, checking out, interacting with the AI chatbot, and submitting feedback. Each session lasts ~60 seconds.

```bash
# View simulator logs
docker compose logs -f simulator
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSIONS_PER_MINUTE` | 2 | Browser sessions started per minute |
| `TARGET_SESSION_DURATION` | 60 | Target duration per session (seconds) |
| `MAX_CONCURRENT_BROWSERS` | 3 | Max concurrent Playwright browsers |

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
| `CHAT_ENABLED` | `false` | Enable AI chatbot (`true`/`false`) |
| `OLLAMA_URL` | `http://ollama:11434` | Ollama server URL |
| `SESSIONS_PER_MINUTE` | 2 | Simulator sessions per minute |
| `TARGET_SESSION_DURATION` | 60 | Session duration (seconds) |
| `MAX_CONCURRENT_BROWSERS` | 3 | Max concurrent browsers |

## Observability in LaunchDarkly

After running for a few minutes, you should see in your LaunchDarkly dashboard:

1. **Traces**: Distributed traces showing request flow through services
2. **Errors**: Errors with source attribution (frontend/backend)
3. **Logs**: Structured logs at different severity levels
4. **Sessions**: User sessions with replay capability
5. **AI Configs Monitoring** (when chat enabled): Token usage, latency, error rates, and user feedback per model variation

### Filtering Tips

- Filter by `source: frontend` or `source: backend`
- Filter by `service: payment-service` to see payment errors
- Filter by `service: chat-service` to see LLM traces
- Look for traces with errors to see where failures occur in the chain

## Troubleshooting

### Services not connecting

```bash
# Check if all containers are running
docker compose ps

# View logs for a specific service
docker compose logs api-gateway
```

### No data in LaunchDarkly

1. Verify your SDK keys are correct in `.env`
2. Check service logs for connection errors
3. Ensure your LaunchDarkly project has Observability enabled

### Chat not working

1. Check `CHAT_ENABLED=true` in `.env`
2. Verify Ollama is running: `docker compose logs ollama` or `curl http://localhost:11434/api/tags`
3. Check chat-service logs: `docker compose logs chat-service`
4. On Mac, native Ollama is recommended for performance (Docker can't use Metal GPU)

## License

MIT
