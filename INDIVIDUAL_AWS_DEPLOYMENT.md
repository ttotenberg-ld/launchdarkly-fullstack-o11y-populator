# AWS Deployment Guide (Individual)

Step-by-step instructions for deploying the LaunchDarkly Observability Demo on a single EC2 GPU instance. This gets you an always-on populator generating traces, logs, errors, sessions, and AI chat data in your LD environment.

> **Note:** This guide is for a single individual deployment. For team deployment with a shared centralized LLM server and per-SE populators, refer to the README.

## What You'll End Up With

- A `g6.xlarge` EC2 instance (NVIDIA L4 GPU) running all 10 microservices, the frontend, Ollama LLM, and the Playwright traffic simulator
- AI chatbot generates real LLM responses (Gemma 3 1B / DeepSeek R1 1.5B) with token usage, latency, and feedback metrics tracked in LD
- Using Spot pricing (~$220/mo) with automatic recovery — if AWS reclaims the instance, it auto-restarts when capacity returns
- During brief Spot interruptions, the chat service gracefully falls back to a "temporarily unavailable" message (no crashes, no data loss — the error itself generates useful observability data)

## Prerequisites

- An AWS account with permissions to create EC2 instances, security groups, and key pairs
- A GitHub personal access token (PAT) with `repo` scope — [create one here](https://github.com/settings/tokens). Password authentication is not supported for Git operations.
- LaunchDarkly SDK key and client-side ID for the environment you want to populate
- An SSH key pair in your target AWS region (or you'll create one during setup)

---

## Step 1: Launch the EC2 Instance

### Spot capacity note

GPU Spot instances aren't available in every availability zone. If you get an **"Insufficient capacity"** error:
- **Console:** Change the **Subnet** dropdown to a different AZ (e.g., try `us-east-1b` instead of `us-east-1a`), or set it to **No preference** to let AWS pick
- **CLI:** Don't specify a subnet — AWS will try all AZs automatically
- **Still failing?** Try `g5.xlarge` instead of `g6.xlarge`, or try a different region (`us-west-2` and `us-east-1` tend to have the most GPU availability)

### Instance type options

| Instance | GPU | VRAM | Spot $/hr | Notes |
|----------|-----|------|-----------|-------|
| `g6.xlarge` | L4 | 24 GB | ~$0.27 | **Recommended** — newer, cheapest, good availability |
| `g5.xlarge` | A10G | 24 GB | ~$0.30 | Good fallback if g6 unavailable |
| `g5.2xlarge` | A10G | 24 GB | ~$0.39 | Same GPU, more CPU/RAM if needed |

All work identically for this project — the 1B models are tiny.

### Via AWS Console

1. Go to **EC2 > Launch Instance**
2. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `ld-o11y-populator` |
| **AMI** | Amazon Linux 2023 |
| **Instance type** | `g6.xlarge` (4 vCPU, 16 GB RAM, NVIDIA L4 24 GB VRAM) |
| **Key pair** | Select or create one — use the **name only**, not the `.pem` filename |
| **Storage** | 100 GB gp3 (models are ~1-2 GB each, plus Docker images) |

3. Under **Network settings**, create a security group with these inbound rules:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| SSH | 22 | Your IP | SSH access |
| Custom TCP | 3000 | Anywhere (0.0.0.0/0) | Frontend UI |
| Custom TCP | 5050 | Anywhere (0.0.0.0/0) | API Gateway (optional, for debugging) |

4. Expand **Advanced details** at the bottom:
   - Under **Purchasing option**, check **Request Spot Instances**
   - Set **Interruption behavior** to **Stop** (not Terminate)
   - Set **Request type** to **Persistent**

5. Click **Launch instance**

### Via AWS CLI

```bash
# Create security group
aws ec2 create-security-group \
  --group-name ld-o11y-populator \
  --description "LaunchDarkly O11y Demo"

SG_ID=$(aws ec2 describe-security-groups \
  --group-names ld-o11y-populator \
  --query 'SecurityGroups[0].GroupId' --output text)

# Add inbound rules
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr $(curl -s https://checkip.amazonaws.com)/32
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 3000 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5050 --cidr 0.0.0.0/0

# Get latest Amazon Linux 2023 AMI
AMI_ID=$(aws ec2 describe-images --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-kernel-*-x86_64" "Name=architecture,Values=x86_64" \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' --output text)

# Create a launch template for Spot with stop behavior
aws ec2 create-launch-template \
  --launch-template-name ld-o11y-populator \
  --launch-template-data '{
    "ImageId": "'"$AMI_ID"'",
    "InstanceType": "g6.xlarge",
    "KeyName": "YOUR_KEY_PAIR_NAME",
    "SecurityGroupIds": ["'"$SG_ID"'"],
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": {"VolumeSize": 100, "VolumeType": "gp3"}
    }],
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [{"Key": "Name", "Value": "ld-o11y-populator"}]
    }],
    "InstanceMarketOptions": {
      "MarketType": "spot",
      "SpotOptions": {
        "SpotInstanceType": "persistent",
        "InstanceInterruptionBehavior": "stop"
      }
    }
  }'

# Launch it
aws ec2 run-instances \
  --launch-template LaunchTemplateName=ld-o11y-populator
```

---

## Step 2: SSH into the Instance

Wait ~60 seconds for the instance to boot, then from your **local terminal** (not AWS CloudShell — your `.pem` file isn't there):

```bash
# Make sure the key file permissions are locked down (SSH will reject it otherwise)
chmod 400 ./YOUR_KEY.pem

ssh -i ./YOUR_KEY.pem ec2-user@<PUBLIC_IP>
```

> Find the public IP in the EC2 console under **Instances > ld-o11y-populator > Public IPv4 address**.

---

## Step 3: Install Docker, Docker Compose, NVIDIA Drivers, and Toolkit

This step installs everything needed. Run these commands in order.

### Docker and Docker Compose

```bash
# Install Docker and Git
sudo dnf install -y docker git

# Start Docker and enable on boot
sudo systemctl enable --now docker

# Add your user to the docker group (so you don't need sudo for docker commands)
sudo usermod -aG docker ec2-user

# Install Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Install Docker Buildx (required for compose build)
sudo curl -SL "https://github.com/docker/buildx/releases/download/v0.22.0/buildx-v0.22.0.linux-amd64" \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
```

### NVIDIA GPU Drivers

The NVIDIA Container Toolkit needs the actual GPU drivers on the host. Amazon Linux 2023's `dnf` packages for NVIDIA drivers are often blocked by modular filtering, so we use the NVIDIA runfile installer instead:

```bash
# Install build dependencies
sudo dnf install -y gcc kernel-devel-$(uname -r) kernel-modules-extra

# Download and install NVIDIA Tesla driver
curl -fSL -O https://us.download.nvidia.com/tesla/550.127.08/NVIDIA-Linux-x86_64-550.127.08.run
sudo sh NVIDIA-Linux-x86_64-550.127.08.run --silent
```

### NVIDIA Container Toolkit

```bash
# Add NVIDIA container toolkit repo
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install and configure
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Log out and back in

Required for the docker group to take effect:

```bash
exit
ssh -i ./YOUR_KEY.pem ec2-user@<PUBLIC_IP>
```

### Verify everything

```bash
# Docker
docker --version
docker compose version
docker buildx version

# GPU driver on host
nvidia-smi

# GPU accessible from Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

You should see your L4 (or A10G) GPU listed in both `nvidia-smi` outputs.

> **If `nvidia-smi` says "command not found"** after the driver install, reboot with `sudo reboot`, SSH back in, and try again.

---

## Step 4: Clone the Repo and Configure

Since this is a private repo, you'll need your GitHub PAT:

```bash
git clone https://<YOUR_GITHUB_USERNAME>:<YOUR_PAT>@github.com/ttotenberg-ld/launchdarkly-fullstack-o11y-populator.git
cd launchdarkly-fullstack-o11y-populator
cp .env.example .env
```

Edit `.env` with your LaunchDarkly credentials:

```bash
nano .env
```

Set these values (make sure there are **no spaces around `=`** and **no trailing whitespace**):

```bash
LD_SDK_KEY=sdk-xxxxx
VITE_LD_CLIENT_SIDE_ID=xxxxx
ENVIRONMENT=production
CHAT_ENABLED=true
OLLAMA_URL=http://ollama:11434
SESSIONS_PER_MINUTE=8
MAX_CONCURRENT_BROWSERS=6
TARGET_SESSION_DURATION=60
```

> **Where to find your keys:** Go to [app.launchdarkly.com](https://app.launchdarkly.com) > **Settings** > **Projects** > your project > your environment. The SDK key starts with `sdk-`. The client-side ID is a shorter alphanumeric string.

> **Traffic volume:** `SESSIONS_PER_MINUTE=8` with `MAX_CONCURRENT_BROWSERS=6` generates solid data volume (~8-10 GB RAM). The LLM runs entirely on the GPU so browser load doesn't affect chat response times. See the README for other traffic settings.

### Verify CHAT_ENABLED is set correctly

This is a common gotcha — if `.env` has whitespace issues, Docker Compose may not pick up the value:

```bash
grep CHAT_ENABLED .env
```

Should show exactly `CHAT_ENABLED=true` with nothing after it.

---

## Step 5: Build and Start

```bash
docker compose --profile local-models up -d --build
```

This will:

- Build 12 Docker images (10 backend services, 1 frontend, 1 simulator)
- Start Ollama with GPU access and automatically pull + warm up `gemma3:1b` and `deepseek-r1:1.5b`
- Start all containers and begin generating traffic immediately

First build takes **5-10 minutes** (downloading base images, installing dependencies, pulling LLM models). Subsequent starts are much faster (~30s for Ollama to reload models from disk).

### Verify everything is running

```bash
docker compose --profile local-models ps
```

You should see all services with status `Up`, including `ollama`:

```
NAME                  STATUS
api-gateway           Up
auth-service          Up
user-service          Up
order-service         Up
payment-service       Up
inventory-service     Up
notification-service  Up
analytics-service     Up
search-service        Up
chat-service          Up
ollama                Up (healthy)
frontend              Up
simulator             Up
```

### Verify the LLM is working

```bash
# Check models are loaded
docker compose exec ollama ollama list

# Test a response (should return in ~1-2s)
curl http://localhost:11434/api/generate -d '{"model":"gemma3:1b","prompt":"hi","stream":false}' | python3 -m json.tool

# Verify chat-service has CHAT_ENABLED=true
docker compose exec chat-service env | grep CHAT
```

If `CHAT_ENABLED` shows `false` despite your `.env` saying `true`, there's likely a whitespace issue in `.env`. Fix it, then restart: `docker compose --profile local-models up -d`

### Check the simulator is generating traffic

```bash
docker compose logs -f simulator
```

You should see output like:
```
Starting browser session for luna@staylightly.io...
Session completed: browsed 4 products, searched 2 times, placed 1 order
Starting browser session for drake@launchbrightly.io...
```

Press `Ctrl+C` to stop following logs.

---

## Step 6: Verify in LaunchDarkly

1. Open `http://<PUBLIC_IP>:3000` in your browser to see the frontend
2. Try the chat widget yourself — responses should come back in ~1-2 seconds
3. Go to your LaunchDarkly dashboard — within 2-3 minutes you should see:
   - **Traces** flowing in (distributed traces across services, including LLM calls)
   - **Errors** appearing (from injected error rates in payment, inventory, etc.)
   - **Logs** at various severity levels
   - **Sessions** with replay data from the simulated browser sessions
   - **AI Configs monitoring** — token usage, latency, error rates, and user feedback per model variation

---

## Managing the Deployment

### Stop all services

```bash
cd ~/launchdarkly-fullstack-o11y-populator
docker compose --profile local-models down
```

### Restart after a stop

```bash
docker compose --profile local-models up -d
```

### Update to latest code

```bash
cd ~/launchdarkly-fullstack-o11y-populator
docker compose --profile local-models down
git pull
docker compose --profile local-models up -d --build
```

### View logs for a specific service

```bash
docker compose logs -f payment-service    # payment errors
docker compose logs -f api-gateway        # all routed requests
docker compose logs -f chat-service       # AI chat requests + LLM responses
docker compose logs -f ollama             # Ollama model loading + inference
```

### Adjust traffic volume

Edit `.env` and restart:

```bash
# Example: more traffic
SESSIONS_PER_MINUTE=10
MAX_CONCURRENT_BROWSERS=8
```

```bash
docker compose --profile local-models up -d
```

### Check resource usage

```bash
docker stats --no-stream
```

A `g6.xlarge` (16 GB RAM + 24 GB VRAM) has plenty of headroom. The LLM runs on the GPU and doesn't compete with the browser-based simulator for CPU/RAM.

---

## How Spot Interruptions Work

You launched this instance as a **persistent Spot request with stop behavior**. Here's what that means in practice:

### What happens during an interruption

| Event | What happens | Impact |
|-------|-------------|--------|
| AWS reclaims Spot capacity | Instance is **stopped** (not terminated). EBS volume preserved. | All services go down. No data generated. |
| Capacity available again | AWS **automatically restarts** the instance. | Docker starts on boot, all containers auto-restart (`restart: unless-stopped`), Ollama reloads models from disk (~30s). Full data generation resumes with no manual intervention. |

### What the chat service does when Ollama is down

If the instance is mid-interruption or Ollama hasn't finished loading yet:

- **Chat service** returns `success: true` with a graceful fallback message ("our support chat is temporarily unavailable") — this still generates traces and error metrics in LD
- **Simulator** catches the error, logs it, and continues the session (browsing, searching, checkout all work fine)
- **Frontend** displays a fallback message in the chat widget — no crash, no blank screen

The error path itself is useful observability data — you'll see it in your LD traces.

### Monitoring Spot status

```bash
# Check if your instance is running or stopped
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=ld-o11y-populator" \
  --query 'Reservations[].Instances[].[State.Name,SpotInstanceRequestId]' \
  --output table
```

### Spot interruption frequency

`g6.xlarge` Spot interruption rates are historically low (<5-10% in most regions). In practice, you may go weeks without an interruption. When one does happen, the downtime is typically minutes — just the time it takes for capacity to free up and the instance to reboot.

### Auto-recovery user data (optional)

For fully hands-off recovery (including after the very first boot), add this as **User Data** in your launch template. This makes the instance self-provisioning — you only need to SSH in once to set your LD keys:

```bash
#!/bin/bash
set -e

# Install Docker (idempotent - skips if already installed)
if ! command -v docker &>/dev/null; then
  dnf install -y docker git
  systemctl enable --now docker
  usermod -aG docker ec2-user

  # Install Docker Compose plugin
  mkdir -p /usr/local/lib/docker/cli-plugins
  curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

  # Install Docker Buildx
  curl -SL "https://github.com/docker/buildx/releases/download/v0.22.0/buildx-v0.22.0.linux-amd64" \
    -o /usr/local/lib/docker/cli-plugins/docker-buildx
  chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

  # Install NVIDIA driver
  dnf install -y gcc kernel-devel-$(uname -r) kernel-modules-extra
  curl -fSL -O https://us.download.nvidia.com/tesla/550.127.08/NVIDIA-Linux-x86_64-550.127.08.run
  sh NVIDIA-Linux-x86_64-550.127.08.run --silent

  # Install NVIDIA Container Toolkit
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
    tee /etc/yum.repos.d/nvidia-container-toolkit.repo
  dnf install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
  systemctl restart docker
fi

# Clone repo if not present
REPO_DIR=/home/ec2-user/launchdarkly-fullstack-o11y-populator
if [ ! -d "$REPO_DIR" ]; then
  git clone https://github.com/ttotenberg-ld/launchdarkly-fullstack-o11y-populator.git "$REPO_DIR"
  cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
  # You'll still need to SSH in once to set LD_SDK_KEY and VITE_LD_CLIENT_SIDE_ID in .env
fi

# Start services (idempotent - Docker Compose handles already-running containers)
cd "$REPO_DIR"
docker compose --profile local-models up -d --build
```

> **Note:** You still need to SSH in **once** after first launch to set your LD keys in `.env`, then restart with `docker compose --profile local-models up -d`. After that, Spot stop/restart cycles are fully automatic.

---

## Troubleshooting

### "Insufficient capacity" when launching Spot

GPU Spot capacity varies by availability zone. Try:
1. Set subnet to **No preference** in the console (or omit subnet in CLI) to let AWS pick the AZ
2. Try a different instance type (`g5.xlarge` instead of `g6.xlarge`, or vice versa)
3. Try a different region (`us-west-2`, `us-east-1` have the most GPU capacity)

### SSH permission denied

- **"UNPROTECTED PRIVATE KEY FILE"** — run `chmod 400 ./your-key.pem` before SSH
- **"Identity file not accessible"** — you're SSHing from AWS CloudShell, which doesn't have your `.pem` file. Use your local terminal instead, or upload the key to CloudShell via **Actions > Upload file**

### nvidia-smi not found after driver install

Reboot the instance and try again:
```bash
sudo reboot
# Wait ~30s, then SSH back in
nvidia-smi
```

### Docker Buildx version error

If you see `compose build requires buildx 0.17.0 or later`:
```bash
sudo curl -SL "https://github.com/docker/buildx/releases/download/v0.22.0/buildx-v0.22.0.linux-amd64" \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
```

### NVIDIA driver install fails (dnf/modular filtering)

Amazon Linux 2023 often blocks NVIDIA driver packages via modular filtering. Use the runfile installer instead (already in Step 3). If you previously tried `dnf install nvidia-driver-latest-dkms` and it failed, that's expected.

### Git clone asks for password

GitHub doesn't support password authentication. Use a personal access token:
```bash
git clone https://<USERNAME>:<PAT>@github.com/ttotenberg-ld/launchdarkly-fullstack-o11y-populator.git
```
Create a PAT at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.

### Containers keep restarting

```bash
# Check which container is failing
docker compose --profile local-models ps

# Read its logs
docker compose logs <service-name>
```

Common causes:
- **Wrong SDK key** — auth/connection errors in logs. Double-check `LD_SDK_KEY` in `.env`
- **Out of memory** — unlikely on `g6.xlarge` (16 GB RAM), but check if you increased `MAX_CONCURRENT_BROWSERS` beyond 8

### Simulator not generating traffic

```bash
docker compose logs simulator
```

Common causes:
- **Frontend not ready yet** — the simulator waits for the frontend to be healthy. Give it a minute after first start
- **Chromium crash** — if you see Playwright errors, reduce `MAX_CONCURRENT_BROWSERS` to 4

### No data in LaunchDarkly

1. Verify your SDK key: `docker compose logs api-gateway | grep -i "launchdarkly\|sdk\|error"`
2. Make sure your LD project has Observability enabled
3. Check that the frontend client-side ID matches the same LD project/environment

### Chat not getting real LLM responses

```bash
# Check Ollama is healthy
docker compose logs ollama

# Check models are loaded
docker compose exec ollama ollama list

# Check GPU is accessible
docker compose exec ollama nvidia-smi

# Check chat-service can reach Ollama
docker compose logs chat-service | grep -i "ollama\|error\|fallback"

# Verify CHAT_ENABLED is actually true inside the container
docker compose exec chat-service env | grep CHAT
```

If `CHAT_ENABLED` shows `false` despite your `.env` saying `true`, there's likely a whitespace or formatting issue in `.env`. Re-edit with `nano .env`, make sure the line is exactly `CHAT_ENABLED=true` with no trailing spaces, save, and restart.

### Can't access http://\<IP\>:3000

1. Verify the security group allows inbound on port 3000 from your IP
2. Check the frontend container is running: `docker compose --profile local-models ps frontend`
3. Make sure you're using the **public** IP, not the private one

---

## Cost Management

### Monthly cost

| Config | Instance | Storage | Total/mo |
|--------|----------|---------|----------|
| Always-on (Spot) | g6.xlarge | 100 GB gp3 | **~$205** |
| Always-on (On-Demand) | g6.xlarge | 100 GB gp3 | ~$650 |
| Business hours only (Spot, 10h × weekdays) | g6.xlarge | 100 GB gp3 | ~$68 |

### Stop when not needed

```bash
# From your local machine
aws ec2 stop-instances --instance-ids <INSTANCE_ID>

# Start it back up
aws ec2 start-instances --instance-ids <INSTANCE_ID>
```

> **Note:** The public IP changes when you stop/start unless you associate an Elastic IP ($3.65/mo when the instance is stopped, free when running).

### Schedule auto stop/start

Use EventBridge + Lambda or a simple cron to run only during business hours:

```bash
# On the EC2 instance, add to crontab (shuts down at 8pm ET, restarts handled by EventBridge)
sudo crontab -e
# Add:
# 0 0 * * * /usr/sbin/shutdown -h now
```

Or use AWS Instance Scheduler for more control.
