# =============================================================================
# LaunchDarkly flags + AI Config used by the fullstack observability populator.
#
# This file provisions ONLY the flags this project actually reads. Other flags
# that may exist in your LaunchDarkly project are out of scope.
#
# All flags here use include_in_snippet = false (this is the default for
# server-side flags, explicit for clarity on the multivariate flags that are
# also evaluated client-side — they need client_side_availability set instead).
# =============================================================================

# -----------------------------------------------------------------------------
# migrate-warehouse-api
# Gates warehouse error injection in inventory-service.
# Evaluated server-side (inventory-service/app.py:151) and client-side (App.jsx
# for event generation), so client_side_availability is enabled.
# -----------------------------------------------------------------------------
resource "launchdarkly_feature_flag" "migrate_warehouse_api" {
  project_key    = var.project_key
  key            = "migrate-warehouse-api"
  name           = "Migrate Warehouse API"
  description    = "Controls warehouse API version. v1=legacy stable (~1% errors), v2=unstable migration (~93% errors), v3=stabilized (clean)."
  variation_type = "string"
  tags           = ["demo", "migration", "error-injection"]

  client_side_availability {
    using_environment_id = true
    using_mobile_key     = false
  }

  variations {
    value       = "v1"
    name        = "v1 — Legacy stable"
    description = "Original warehouse API. Low background error rate (~1%)."
  }
  variations {
    value       = "v2"
    name        = "v2 — Unstable migration"
    description = "New warehouse API v2 with injected error scenarios (~93% composite error rate)."
  }
  variations {
    value       = "v3"
    name        = "v3 — Stabilized"
    description = "v2 after stabilization — clean, zero injected errors."
  }

  defaults {
    on_variation  = 0 # v1
    off_variation = 0 # v1
  }
}

# -----------------------------------------------------------------------------
# payment-processor-migration
# Routes DB pathology scenarios in payment-service. Also evaluated in
# order-service /checkout up front (for guarded-rollout sample volume) but
# that evaluation is log + span-tag only, not behavior-driving.
# Server-side only — not read client-side.
# -----------------------------------------------------------------------------
resource "launchdarkly_feature_flag" "payment_processor_migration" {
  project_key    = var.project_key
  key            = "payment-processor-migration"
  name           = "Payment Processor Migration"
  description    = "Routes payment-service DB pathology scenarios. v1=legacy stable, v2=in-flight migration (slow queries, planner regressions, pool pressure, rollbacks), v3=migration complete."
  variation_type = "string"
  tags           = ["demo", "migration", "guarded-rollout"]

  client_side_availability {
    using_environment_id = false
    using_mobile_key     = false
  }

  variations {
    value       = "v1"
    name        = "v1 — Legacy stable"
    description = "Clean baseline processor."
  }
  variations {
    value       = "v2"
    name        = "v2 — In-flight migration"
    description = "Injects DB pathologies (pg_sleep, seq scan regressions, pool holds, forced rollbacks)."
  }
  variations {
    value       = "v3"
    name        = "v3 — Migration complete"
    description = "Same code path as v1. 'Success' variation for before/after dashboards."
  }

  defaults {
    on_variation  = 0 # v1
    off_variation = 0 # v1
  }
}

# -----------------------------------------------------------------------------
# session-replay-privacy
# Read client-side in frontend/src/main.jsx via a pre-SDK-init clientsdk
# evalx fetch — SessionReplay's privacySetting is constructor-only.
# -----------------------------------------------------------------------------
resource "launchdarkly_feature_flag" "session_replay_privacy" {
  project_key    = var.project_key
  key            = "session-replay-privacy"
  name           = "Session Replay Privacy"
  description    = "Privacy level passed to @launchdarkly/session-replay constructor. Read once at page load, pre-SDK-init."
  variation_type = "string"
  tags           = ["demo", "session-replay"]

  client_side_availability {
    using_environment_id = true
    using_mobile_key     = false
  }

  variations {
    value       = "none"
    name        = "None"
    description = "No masking. Use only in synthetic/demo environments."
  }
  variations {
    value       = "default"
    name        = "Default"
    description = "LaunchDarkly Session Replay default masking."
  }
  variations {
    value       = "strict"
    name        = "Strict"
    description = "Aggressive masking of all text/inputs."
  }

  defaults {
    on_variation  = 1 # default
    off_variation = 1 # default
  }
}

# -----------------------------------------------------------------------------
# product-card-layout
# Product card UI variant. Read in Products.jsx, ProductCard.jsx, Checkout.jsx.
# Tagged as layout_variant on every funnel metric.
# -----------------------------------------------------------------------------
resource "launchdarkly_feature_flag" "product_card_layout" {
  project_key    = var.project_key
  key            = "product-card-layout"
  name           = "Product Card Layout"
  description    = "Product card UI variant. Tagged as layout_variant on cart/checkout/search metrics for conversion slicing."
  variation_type = "string"
  tags           = ["demo", "funnel", "ui"]

  client_side_availability {
    using_environment_id = true
    using_mobile_key     = false
  }

  variations {
    value       = "standard"
    name        = "Standard (control)"
    description = "Image, name, price, Add to Cart button."
  }
  variations {
    value       = "minimal"
    name        = "Minimal"
    description = "Image + name only. Price revealed on hover."
  }
  variations {
    value       = "detailed"
    name        = "Detailed"
    description = "Adds rating stars, stock count urgency, free-shipping badge."
  }

  defaults {
    on_variation  = 0 # standard
    off_variation = 0 # standard
  }
}

# -----------------------------------------------------------------------------
# promo-banner
# Site-wide banner. Read in PromoBanner.jsx + tagged on checkout metrics.
# -----------------------------------------------------------------------------
resource "launchdarkly_feature_flag" "promo_banner" {
  project_key    = var.project_key
  key            = "promo-banner"
  name           = "Promo Banner"
  description    = "Site-wide promo banner variant. Tagged as promo_variant on checkout metrics."
  variation_type = "string"
  tags           = ["demo", "funnel", "ui"]

  client_side_availability {
    using_environment_id = true
    using_mobile_key     = false
  }

  variations {
    value       = "none"
    name        = "None (control)"
    description = "Banner hidden."
  }
  variations {
    value       = "free-shipping-50"
    name        = "Free shipping over $50"
    description = "Free shipping messaging."
  }
  variations {
    value       = "percent-off"
    name        = "20% off first order"
    description = "Discount messaging."
  }
  variations {
    value       = "urgency"
    name        = "Flash sale"
    description = "Flash sale with live countdown timer."
  }

  defaults {
    on_variation  = 0 # none
    off_variation = 0 # none
  }
}

# -----------------------------------------------------------------------------
# AI Config: support-chatbot
# Used in backend/services/chat-service/app.py:325
#   ai_client.completion_config('support-chatbot', context, DEFAULT_AI_CONFIG, {})
# Variations select model name + system prompt + hyperparameters.
# -----------------------------------------------------------------------------
resource "launchdarkly_ai_config" "support_chatbot" {
  project_key = var.project_key
  key         = "support-chatbot"
  name        = "Support Chatbot"
  description = "Selects LLM model, system prompt, and hyperparameters for the chat-service support bot. Metrics (tokens, latency, feedback) are tracked per-variation via the LD AI SDK tracker."
  tags        = ["demo", "llm"]
}

resource "launchdarkly_ai_config_variation" "support_chatbot_gemma" {
  project_key = var.project_key
  config_key  = launchdarkly_ai_config.support_chatbot.key
  key         = "gemma3-1b"
  name        = "Gemma 3 1B"

  model = jsonencode({
    name = "gemma3:1b"
    parameters = {
      temperature = 0.7
      max_tokens  = 256
      top_p       = 0.9
    }
  })

  messages {
    role    = "system"
    content = "You are a helpful customer support agent for an e-commerce store that sells developer tools and feature management products. Be concise, friendly, and helpful. Keep responses under 3 sentences."
  }
}

resource "launchdarkly_ai_config_variation" "support_chatbot_deepseek" {
  project_key = var.project_key
  config_key  = launchdarkly_ai_config.support_chatbot.key
  key         = "deepseek-r1-1-5b"
  name        = "DeepSeek R1 1.5B"

  model = jsonencode({
    name = "deepseek-r1:1.5b"
    parameters = {
      temperature = 0.6
      max_tokens  = 512
      top_p       = 0.95
      top_k       = 40
    }
  })

  messages {
    role    = "system"
    content = "You are a helpful customer support agent for an e-commerce store that sells developer tools and feature management products. Be concise, friendly, and helpful. Keep responses under 3 sentences."
  }
}
