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

## AWS Deployment

This project can be deployed to AWS for team demos or persistent data generation. Two approaches:

### Option A: Single EC2 Instance (Simplest)

Run everything on one instance — good for demos and short-lived deployments.

#### 1. Launch an EC2 instance

| Setting | Value |
|---------|-------|
| **AMI** | Amazon Linux 2023 or Ubuntu 24.04 |
| **Instance type (no LLM)** | `t3.large` (2 vCPU, 8 GB) |
| **Instance type (with LLM)** | `g5.xlarge` (1x A10G GPU, 24 GB, 4 vCPU, 16 GB RAM) |
| **Storage** | 50 GB gp3 (100 GB if using LLMs — models are ~1-2 GB each) |
| **Security group** | Inbound: 22 (SSH), 3000 (frontend), 5050 (API gateway) |

#### 2. Install Docker

```bash
# Amazon Linux 2023
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Install Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m) \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Log out and back in for group changes
exit
```

#### 3. (GPU instances only) Install NVIDIA Container Toolkit

```bash
# Add NVIDIA repo
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU is accessible
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

#### 4. Clone and configure

```bash
git clone <your-repo-url> && cd launchdarkly-fullstack-o11y-populator
cp .env.example .env
```

Edit `.env`:
```bash
LD_SDK_KEY=sdk-xxxxx
VITE_LD_CLIENT_SIDE_ID=xxxxx
CHAT_ENABLED=true              # or false for no-LLM mode
OLLAMA_URL=http://ollama:11434 # use Docker Ollama on GPU instances
```

#### 5. Start services

```bash
# No LLM (t3.large)
docker compose up -d --build

# With LLM on GPU instance (g5.xlarge)
docker compose --profile local-models up -d --build
```

#### 6. Access the demo

- Frontend: `http://<ec2-public-ip>:3000`
- API Gateway: `http://<ec2-public-ip>:5050`

> **Tip:** For HTTPS, put an Application Load Balancer (ALB) in front with an ACM certificate, or use Caddy as a reverse proxy with automatic Let's Encrypt.

---

### Option B: ECS Fargate + Separate GPU for Ollama

Better for longer-lived deployments or team-shared environments.

#### Architecture

```
┌──────────────────────────────────────────────────────┐
│                  ECS Cluster (Fargate)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ frontend │ │ gateway  │ │ services │ × 9          │
│  │  :3000   │ │  :5050   │ │ :5001-09 │             │
│  └──────────┘ └──────────┘ └──────────┘             │
│                                  │                    │
│                                  ▼                    │
│                          ┌──────────────┐            │
│                          │ EC2 g5.xlarge │            │
│                          │   Ollama      │            │
│                          │   :11434      │            │
│                          └──────────────┘            │
└──────────────────────────────────────────────────────┘
         │
         ▼
   ┌───────────┐
   │    ALB    │ ← HTTPS
   └───────────┘
```

#### Steps

1. **Push images to ECR:**
   ```bash
   # Create repositories
   for svc in frontend api-gateway auth-service user-service order-service \
     payment-service inventory-service notification-service analytics-service \
     search-service chat-service simulator; do
     aws ecr create-repository --repository-name ld-o11y-demo/$svc
   done

   # Build and push (repeat for each service)
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker compose build
   for svc in frontend api-gateway auth-service user-service order-service \
     payment-service inventory-service notification-service analytics-service \
     search-service chat-service simulator; do
     docker tag launchdarkly-fullstack-o11y-populator-$svc:latest \
       <account>.dkr.ecr.<region>.amazonaws.com/ld-o11y-demo/$svc:latest
     docker push <account>.dkr.ecr.<region>.amazonaws.com/ld-o11y-demo/$svc:latest
   done
   ```

2. **Launch Ollama on a GPU EC2 instance:**
   ```bash
   # On a g5.xlarge with NVIDIA drivers installed
   docker run -d --gpus all -p 11434:11434 \
     -v ollama_data:/root/.ollama \
     --name ollama --restart unless-stopped \
     ollama/ollama

   # Pull models
   docker exec ollama ollama pull gemma3:1b
   docker exec ollama ollama pull deepseek-r1:1.5b
   ```
   Note the private IP of this instance for `OLLAMA_URL`.

3. **Create ECS task definitions** for each service, passing environment variables:
   - `LD_SDK_KEY`, `VITE_LD_CLIENT_SIDE_ID`
   - `CHAT_ENABLED=true`
   - `OLLAMA_URL=http://<ollama-private-ip>:11434`

4. **Create an ALB** with target groups pointing to the frontend (port 3000) and API gateway (port 5050).

---

### LLM Response Times

| Setup | Hardware | Response Time | Notes |
|-------|----------|---------------|-------|
| Docker on Mac | CPU only (M-series GPU inaccessible) | ~20-40s | Docker VM can't access Metal GPU |
| Native Ollama on Mac | Apple Silicon (Metal) | ~1-3s | Recommended for local dev |
| `g5.xlarge` (A10G) | NVIDIA A10G 24 GB | ~0.5-2s | Best price/performance for 1B models |
| `g5.2xlarge` (A10G) | A10G + 8 vCPU, 32 GB RAM | ~0.5-1.5s | More headroom for concurrent requests |
| `g6.xlarge` (L4) | NVIDIA L4 24 GB | ~0.5-2s | Newer GPU, similar performance |

> Response times are for Gemma 3 1B / DeepSeek R1 1.5B generating ~100-200 token responses. DeepSeek R1 may be slightly slower due to hidden `<think>` reasoning tokens generated before the visible response.

---

### Team Deployment: Always-On Per-SE Populators

For teams where each Solutions Engineer has their own LaunchDarkly demo instance, the recommended architecture is:

- **Per-SE populator** — a lightweight `t3.large` running the full stack *without* LLM (`CHAT_ENABLED=false` or pointing at the shared LLM)
- **One centralized LLM server** — a single GPU instance running Ollama, shared across all SE populators

```
┌──────────────────────────────────────────────────────────┐
│                   Shared LLM Server                       │
│                  g5.xlarge (A10G GPU)                      │
│                  Ollama :11434                             │
│             gemma3:1b + deepseek-r1:1.5b                  │
└──────────────────────────────────────────────────────────┘
          ▲            ▲            ▲            ▲
          │            │            │            │
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ SE #1    │ │ SE #2    │ │ SE #3    │ │ SE #N    │
   │ t3.large │ │ t3.large │ │ t3.large │ │ t3.large │
   │ populator│ │ populator│ │ populator│ │ populator│
   │ LD Env A │ │ LD Env B │ │ LD Env C │ │ LD Env N │
   └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Each SE populator's `.env`:
```bash
LD_SDK_KEY=sdk-xxxxx              # SE's own LD environment
VITE_LD_CLIENT_SIDE_ID=xxxxx      # SE's own client-side ID
CHAT_ENABLED=true
OLLAMA_URL=http://<shared-ollama-private-ip>:11434
```

#### Team Cost Estimates

| Component | Instance | Per Unit/mo | Qty | Monthly Cost |
|-----------|----------|-------------|-----|--------------|
| SE populator (no LLM) | `t3.large` | ~$60 | N | N × $60 |
| Shared LLM server | `g5.xlarge` | ~$730 | 1 | $730 |
| Shared LLM server (Spot) | `g5.xlarge` | ~$220 | 1 | $220 |

**Examples:**

| Team Size | Populators | LLM Server (On-Demand) | LLM Server (Spot) | Total (On-Demand) | Total (Spot) |
|-----------|------------|------------------------|--------------------|-------------------|--------------|
| 5 SEs | 5 × $60 = $300 | $730 | $220 | **$1,030/mo** | **$520/mo** |
| 10 SEs | 10 × $60 = $600 | $730 | $220 | **$1,330/mo** | **$820/mo** |
| 20 SEs | 20 × $60 = $1,200 | $730 | $220 | **$1,930/mo** | **$1,420/mo** |
| 30 SEs | 30 × $60 = $1,800 | $1,460 (×2) | $440 (×2) | **$3,260/mo** | **$2,240/mo** |

#### Centralized LLM Scaling

How much load can one Ollama GPU instance handle?

**Per-populator LLM load** (default settings: 2 sessions/min, 50% open chatbot, 1-3 questions):
- ~1.5 chat requests per minute per populator
- Each request generates ~100-200 tokens
- Each request takes ~1-2s of GPU time on A10G

**Single `g5.xlarge` (1× A10G) capacity:**

| Metric | Value |
|--------|-------|
| Sequential throughput | ~30-40 requests/min |
| Avg GPU time per request | ~1.5s |
| Concurrent requests (Ollama queues) | 1 active + queued |
| **Max populators before queueing** | **~20-25** |
| **Max populators before degraded UX** | **~30-35** (responses start taking 3-5s) |

**When to scale up:**

| Populators | Recommendation |
|------------|----------------|
| 1-20 | Single `g5.xlarge` — all requests served in ~1-2s |
| 20-35 | Single `g5.xlarge` — still works, occasional 3-5s responses under load |
| 35-50 | Upgrade to `g5.2xlarge` or add a second `g5.xlarge` behind a load balancer |
| 50+ | Two `g5.xlarge` instances with round-robin DNS or an NLB |

> **Note:** These estimates assume default simulator settings (2 sessions/min, 50% chat rate). If SEs increase `SESSIONS_PER_MINUTE` or run live demos with manual chatbot usage simultaneously, effective load increases. The models are small (1-1.5B params) so they fit entirely in GPU memory — the bottleneck is sequential generation, not memory.

> **Scaling tip:** Ollama supports `OLLAMA_NUM_PARALLEL` to process multiple requests concurrently (sharing GPU). Setting `OLLAMA_NUM_PARALLEL=4` on the shared server can increase throughput at the cost of slightly slower individual responses. This can push a single `g5.xlarge` to comfortably handle 40+ populators.

---

### General Cost Saving Tips

- Use **Spot Instances** for the GPU server (up to 70% savings for `g5.xlarge`). Spot interruptions are fine — chat just returns the "down for maintenance" fallback until the instance recovers
- Use **Scheduled Actions** or Lambda-based stop/start to shut down populators outside business hours (e.g., run 10hrs/day × weekdays = ~30% of 24/7 cost)
- The no-LLM mode on `t3.large` is very affordable for always-on data generation without AI features

## License

MIT
