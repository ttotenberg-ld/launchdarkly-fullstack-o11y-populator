"""
Chat Service - AI-powered support chatbot using local LLMs via Ollama.
Port: 5009

Model selection and system prompts are controlled at runtime via LaunchDarkly
AI Configs.  Metrics (token usage, latency, success/error) are tracked via the
LD AI SDK tracker AND auto-captured as OpenTelemetry LLM spans via OpenLLMetry.
"""

import os
import re
import time
import uuid
from collections import OrderedDict
import requests as http_requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.users import get_random_user, get_user_context

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'chat-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://ollama:11434')

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize LD AI Client for AI Config retrieval + metric tracking
import ldclient
from ldai.client import LDAIClient, AICompletionConfigDefault, ModelConfig, LDMessage
from ldai.tracker import TokenUsage, FeedbackKind

ai_client = LDAIClient(ldclient.get())
print(f"  ✓ LDAIClient initialized for AI Configs")

# Register OpenLLMetry Ollama instrumentation AFTER LD SDK but BEFORE making
# LLM calls.  This auto-captures ollama.chat() as OpenTelemetry LLM spans
# (model, prompts, responses, tokens) which flow to LD Observability → Traces.
try:
    from opentelemetry.instrumentation.ollama import OllamaInstrumentor
    OllamaInstrumentor().instrument()
    print(f"  ✓ OpenLLMetry Ollama instrumentation enabled")
except ImportError:
    print(f"  ⚠ opentelemetry-instrumentation-ollama not installed, LLM spans will not be auto-captured")

# Now initialize ollama client
import ollama as ollama_client

# Initialize Flask app
app = Flask(__name__)
USER_HEADERS = ['X-User-Key', 'X-User-Name', 'X-User-Email', 'X-User-Plan',
                'X-User-Role', 'X-User-Metro', 'X-User-Country']
CORS(app, expose_headers=['traceparent', 'tracestate'],
     allow_headers=['Content-Type', 'traceparent', 'tracestate'] + USER_HEADERS)

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)

# Default AI Config fallback (used when LD is unreachable)
DEFAULT_AI_CONFIG = AICompletionConfigDefault(
    enabled=True,
    model=ModelConfig(name="gemma3:1b"),
    messages=[
        LDMessage(
            role="system",
            content="You are a helpful customer support agent for an e-commerce store "
                    "that sells developer tools and feature management products. "
                    "Be concise, friendly, and helpful. Keep responses under 3 sentences.",
        ),
    ],
)

# Regex to strip <think>...</think> blocks from DeepSeek R1 output
THINK_TAG_RE = re.compile(r'<think>.*?</think>', re.DOTALL)

# Mapping from LD AI Config parameter names (OpenAI-style) → Ollama option names.
# LD's AI Config UI uses OpenAI conventions; Ollama has its own naming for some.
# Parameters that share the same name in both systems are passed through as-is.
LD_TO_OLLAMA_PARAMS = {
    'temperature': 'temperature',
    'top_p': 'top_p',
    'top_k': 'top_k',
    'max_tokens': 'num_predict',      # OpenAI → Ollama naming difference
    'maxTokens': 'num_predict',       # camelCase variant
    'seed': 'seed',
    'stop': 'stop',
    'repeat_penalty': 'repeat_penalty',
    'presence_penalty': 'presence_penalty',
    'frequency_penalty': 'frequency_penalty',
}

FALLBACK_RESPONSE = (
    "I'm sorry, our support chat is temporarily unavailable. "
    "Please try again in a moment."
)

# Short-lived cache of trackers keyed by generation ID.  When the frontend
# sends delayed feedback (thumbs up/down), we look up the original tracker
# and call track_feedback() so the metric is attributed to the correct
# AI Config variation.  Capped at 500 entries to avoid unbounded growth.
MAX_TRACKER_CACHE = 500
_tracker_cache: OrderedDict = OrderedDict()


def _user_from_headers() -> dict:
    """Reconstruct user from X-User-* headers.  Falls back to random user."""
    key = request.headers.get('X-User-Key')
    if not key:
        return get_random_user()

    user = {'key': key}
    _MAP = {
        'X-User-Name': 'name',
        'X-User-Email': 'email',
        'X-User-Plan': 'plan',
        'X-User-Role': 'role',
        'X-User-Metro': 'metro',
        'X-User-Country': 'country',
    }
    for header, attr in _MAP.items():
        val = request.headers.get(header)
        if val:
            user[attr] = val
    return user


def _build_ollama_options(config_value) -> dict:
    """Extract model parameters from the LD AI Config and map them to Ollama options.

    The AI Config UI lets you set hyperparameters (temperature, max_tokens, etc.)
    at the model-config or variation level.  These arrive in
    ``config_value.model.parameters`` as a dict.  We translate any known keys
    to Ollama's naming convention and pass them through.
    """
    options = {}
    params = getattr(config_value.model, 'parameters', None) if config_value.model else None
    if not params:
        return options

    for ld_key, ollama_key in LD_TO_OLLAMA_PARAMS.items():
        val = params.get(ld_key)
        if val is not None:
            options[ollama_key] = val

    # Pass through any remaining params that aren't in our map —
    # they may be Ollama-native options set via LD custom parameters.
    for key, val in params.items():
        if key not in LD_TO_OLLAMA_PARAMS and key not in options:
            options[key] = val

    return options


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks produced by DeepSeek R1."""
    return THINK_TAG_RE.sub('', text).strip()


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    # Also check Ollama connectivity
    ollama_ok = False
    try:
        resp = http_requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = resp.status_code == 200
    except Exception:
        pass

    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'ollama_url': OLLAMA_URL,
        'ollama_connected': ollama_ok,
    })


@app.route('/chat', methods=['POST'])
def chat():
    """Handle a chat message using an LLM via Ollama.

    The model and system prompt are determined by the LaunchDarkly AI Config
    'support-chatbot'.  Different AI Config variations can serve different
    models (e.g. Gemma 3 1B vs DeepSeek R1 1.5B) without code changes.
    """
    with start_span('chat.completion') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'}), 400

        span.set_attribute('message_length', len(user_message))

        # Build LD context from user headers
        user = _user_from_headers()
        context = get_user_context(user)

        # Retrieve AI Config — determines which model + system prompt to use
        config_value = ai_client.completion_config(
            'support-chatbot',
            context,
            DEFAULT_AI_CONFIG,
            {},
        )
        tracker = config_value.tracker

        model_name = config_value.model.name if config_value.model else 'gemma3:1b'
        span.set_attribute('llm.model', model_name)

        # Build messages: system prompt from AI Config + user's message
        messages = []
        if config_value.messages:
            for msg in config_value.messages:
                messages.append({'role': msg.role, 'content': msg.content})
        messages.append({'role': 'user', 'content': user_message})

        # Extract hyperparameters from AI Config → Ollama options
        ollama_options = _build_ollama_options(config_value)
        if ollama_options:
            span.set_attribute('llm.parameters', str(ollama_options))

        record_log(f"Chat request: model={model_name}, msg_len={len(user_message)}, params={ollama_options or '{}'}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/chat'),
            'model': model_name,
            'user_key': user.get('key', 'unknown'),
        })

        # Call Ollama — this is auto-captured by OpenLLMetry as an LLM span
        try:
            ollama_cli = ollama_client.Client(host=OLLAMA_URL)
            start_t = time.time()
            response = ollama_cli.chat(
                model=model_name,
                messages=messages,
                options=ollama_options if ollama_options else None,
            )
            duration_ms = (time.time() - start_t) * 1000

            # Extract response text and strip <think> tags (DeepSeek R1)
            answer = _strip_think_tags(response['message']['content'])

            # Track metrics via LD AI SDK tracker
            tracker.track_success()

            input_tokens = response.get('prompt_eval_count', 0)
            output_tokens = response.get('eval_count', 0)
            tracker.track_tokens(TokenUsage(
                input=input_tokens,
                output=output_tokens,
                total=input_tokens + output_tokens,
            ))

            # Use Ollama's own duration if available, otherwise our measured time
            ollama_duration = response.get('total_duration')
            if ollama_duration:
                duration_ms = ollama_duration / 1_000_000  # nanoseconds → ms
            tracker.track_duration(duration_ms)

            span.set_attribute('llm.input_tokens', input_tokens)
            span.set_attribute('llm.output_tokens', output_tokens)
            span.set_attribute('llm.duration_ms', round(duration_ms, 1))

            record_log(
                f"Chat response: model={model_name}, tokens={input_tokens}+{output_tokens}, "
                f"duration={duration_ms:.0f}ms",
                LEVELS['info'],
                {
                    **get_common_attributes(SERVICE_NAME, '/chat'),
                    'model': model_name,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'duration_ms': round(duration_ms, 1),
                },
            )

            # Cache the tracker so delayed feedback can be attributed
            generation_id = uuid.uuid4().hex[:16]
            _tracker_cache[generation_id] = tracker
            # Evict oldest entries if cache is full
            while len(_tracker_cache) > MAX_TRACKER_CACHE:
                _tracker_cache.popitem(last=False)

            return jsonify({
                'success': True,
                'response': answer,
                'model': model_name,
                'generation_id': generation_id,
                'tokens': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': input_tokens + output_tokens,
                },
                'duration_ms': round(duration_ms, 1),
                'service': SERVICE_NAME,
            })

        except Exception as e:
            tracker.track_error()
            record_exception(e, {
                **get_common_attributes(SERVICE_NAME, '/chat'),
                'model': model_name,
                'error_type': type(e).__name__,
            })

            return jsonify({
                'success': True,  # Don't fail the session
                'response': FALLBACK_RESPONSE,
                'model': model_name,
                'fallback': True,
                'service': SERVICE_NAME,
            })


@app.route('/chat/feedback', methods=['POST'])
def chat_feedback():
    """Record thumbs-up / thumbs-down feedback on an AI chat response.

    Expects JSON: { "generation_id": "...", "sentiment": "positive" | "negative" }

    Uses the cached tracker from the original /chat call so the feedback
    metric ($ld:ai:feedback:user:positive / negative) is attributed to the
    correct AI Config variation.
    """
    with start_span('chat.feedback') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        data = request.get_json() or {}
        generation_id = data.get('generation_id', '')
        sentiment = data.get('sentiment', '')

        if sentiment not in ('positive', 'negative'):
            return jsonify({'success': False, 'error': 'sentiment must be "positive" or "negative"'}), 400

        span.set_attribute('feedback.sentiment', sentiment)
        span.set_attribute('feedback.generation_id', generation_id)

        tracker = _tracker_cache.get(generation_id)
        if not tracker:
            # Tracker expired or unknown — still log but can't attribute to variation
            record_log(
                f"Chat feedback (unattributed): sentiment={sentiment}, gen_id={generation_id}",
                LEVELS['warning'],
                get_common_attributes(SERVICE_NAME, '/chat/feedback'),
            )
            return jsonify({'success': True, 'attributed': False})

        kind = FeedbackKind.Positive if sentiment == 'positive' else FeedbackKind.Negative
        tracker.track_feedback({"kind": kind})

        record_log(
            f"Chat feedback: sentiment={sentiment}, gen_id={generation_id}",
            LEVELS['info'],
            {
                **get_common_attributes(SERVICE_NAME, '/chat/feedback'),
                'sentiment': sentiment,
                'generation_id': generation_id,
            },
        )

        return jsonify({'success': True, 'attributed': True})


# Global error handler
@app.errorhandler(Exception)
def handle_exception(error):
    """Global error handler that records all exceptions."""
    status_code = getattr(error, 'status_code', 500)
    error_type = getattr(error, 'error_type', type(error).__name__)

    record_exception(error, {
        **get_common_attributes(SERVICE_NAME, request.path),
        'error_type': error_type,
        'method': request.method,
    })

    return jsonify({
        'success': False,
        'error': error_type,
        'message': str(error),
        'service': SERVICE_NAME,
    }), status_code


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'message': 'LaunchDarkly AI Chat Service',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'ollama_url': OLLAMA_URL,
        'endpoints': ['/health', '/chat', '/chat/feedback'],
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5009))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
