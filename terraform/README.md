# Terraform — LaunchDarkly resource provisioning

Provisions the feature flags and AI Config this project reads into a LaunchDarkly project **you own**. You must supply your own project key — there is no default.

## What gets created

### Feature flags

| Key | Type | Variations |
|---|---|---|
| `migrate-warehouse-api` | string (client-side enabled) | `v1` / `v2` / `v3` |
| `payment-processor-migration` | string (server-side only) | `v1` / `v2` / `v3` |
| `session-replay-privacy` | string (client-side enabled) | `none` / `default` / `strict` |
| `product-card-layout` | string (client-side enabled) | `standard` / `minimal` / `detailed` |
| `promo-banner` | string (client-side enabled) | `none` / `free-shipping-50` / `percent-off` / `urgency` |

### AI Config

- `support-chatbot` with two variations: `gemma3-1b` and `deepseek-r1-1-5b`. Each variation bundles the model name, a system prompt, and hyperparameters (temperature, max_tokens, top_p, top_k where applicable).

See [`flags.tf`](./flags.tf) for per-resource docs and the exact variation values / descriptions. Mechanics (where each flag is evaluated, what it gates) live in [`../AGENTS.md`](../AGENTS.md).

## Usage

**Prereqs:**
- Terraform >= 1.5
- A LaunchDarkly **project you own** (Terraform won't create one — only flags within an existing project). Note the project key.
- A LaunchDarkly API access token with write access to flags + AI Configs in that project. Create one at `Account settings → Authorization → Access tokens`.

**Warning:** Resources Terraform creates will be owned by Terraform state. Don't run `terraform apply` against a project where these flag keys already exist and are managed elsewhere — you'll fight state. Use a fresh project or manually import existing resources first.

```bash
# 1. Set your LD project key (REQUIRED — no default)
export TF_VAR_project_key="your-project-key"        # e.g. your-name-demo

# 2. Set the access token
export TF_VAR_launchdarkly_access_token="api-xxxxxxxx"
# (or: export LAUNCHDARKLY_ACCESS_TOKEN="api-xxxxxxxx")

# 3. Initialize
cd terraform
terraform init

# 4. Review the plan
terraform plan

# 5. Apply
terraform apply
```

Alternative: copy `terraform.tfvars.example` to `terraform.tfvars` (git-ignored) with your per-machine values so you don't have to re-export them each shell:

```bash
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your project key + access token
```

## Design notes

- Every flag's `on_variation` / `off_variation` defaults to a safe "control" value (v1, none, standard). Targeting rules and env-specific overrides are intentionally NOT managed here — set those via the LD UI so SEs can freely toggle variations during demos without fighting Terraform state.
- `client_side_availability.using_environment_id` is true for the four flags evaluated client-side (`migrate-warehouse-api`, `session-replay-privacy`, `product-card-layout`, `promo-banner`). `payment-processor-migration` is server-only.
- The AI Config is provisioned via `launchdarkly_ai_config` + `launchdarkly_ai_config_variation`. The `model` field takes a JSON-encoded inline config — `parameters` use LD's OpenAI-style names (`max_tokens`, `top_p`) which chat-service maps to Ollama's native names at runtime.

## Related

- [`../AGENTS.md`](../AGENTS.md) — per-flag table with file:line evaluation sites and behavioral details.
- [`../SIGNALS.md`](../SIGNALS.md) — what signals each flag drives in LD Observability.
