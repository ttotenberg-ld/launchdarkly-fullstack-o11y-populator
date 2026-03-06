"""
User generation for LaunchDarkly Observability Demo sessions.

Generates unique users with UUID-based keys and rich metadata that flows
consistently through the entire stack: simulator → frontend → backend.
"""

import random
import uuid
from ldclient import Context

# Attribute pools — match the frontend's api.js lists exactly
PLANS = ['free', 'silver', 'gold', 'platinum', 'diamond']
ROLES = ['reader', 'writer', 'admin']
METROS = ['New York', 'Chicago', 'Minneapolis', 'Atlanta', 'Los Angeles', 'San Francisco', 'Denver', 'Boston']
COUNTRIES = ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'BR', 'IN', 'MX']

# LaunchDarkly-punny name/email pool for flavor
_NAME_POOL = [
    {"name": "Luna Darksworth", "email": "luna@staylightly.io"},
    {"name": "Lance Dimly", "email": "lance@darklaunchly.com"},
    {"name": "Darcy Launch", "email": "darcy@lunchdarkly.net"},
    {"name": "Larry Duskman", "email": "larry@launchdorkly.io"},
    {"name": "Lydia Twilight", "email": "lydia@dimlylaunch.com"},
    {"name": "Drake Moonson", "email": "drake@launchbrightly.io"},
    {"name": "Dawn Flagworth", "email": "dawn@toggledarkly.com"},
    {"name": "Felix Feature", "email": "felix@flaglaunchly.io"},
    {"name": "Sage Rollout", "email": "sage@rolldarkly.net"},
    {"name": "Nova Experiment", "email": "nova@launchsoftly.io"},
    {"name": "River Toggle", "email": "river@darklylaunch.com"},
    {"name": "Stella Variant", "email": "stella@launchquickly.io"},
    {"name": "Atlas Segment", "email": "atlas@lightlylaunch.net"},
    {"name": "Ivy Targeting", "email": "ivy@launchsnarkly.com"},
    {"name": "Max Context", "email": "max@launchdimly.io"},
    {"name": "Zara Percentage", "email": "zara@darklaunchery.net"},
    {"name": "Quinn Prerequisite", "email": "quinn@launchduskly.com"},
    {"name": "Blake Fallthrough", "email": "blake@dawnlaunchly.io"},
    {"name": "Morgan Targeting", "email": "morgan@launchdaily.net"},
    {"name": "Casey Killswitch", "email": "casey@featureflagly.com"},
]

# Backward-compatible static personas (deprecated — use get_random_user())
USER_PERSONAS = [
    {"key": f"usr_{i+1:03d}", **_NAME_POOL[i]}
    for i in range(len(_NAME_POOL))
]


def get_random_user() -> dict:
    """
    Generate a user with a unique UUID key and random attributes.

    Each call produces a fresh user identity that matches the attribute
    schema expected by the frontend (plan, role, metro, country) and
    is consistent across the full request chain.
    """
    persona = random.choice(_NAME_POOL)
    return {
        "key": f"usr-{uuid.uuid4()}",
        "name": persona["name"],
        "email": persona["email"],
        "plan": random.choice(PLANS),
        "role": random.choice(ROLES),
        "metro": random.choice(METROS),
        "country": random.choice(COUNTRIES),
    }


def get_user_context(user: dict = None) -> Context:
    """
    Create a LaunchDarkly context from a user dict.
    If no user is provided, generates a random one.
    """
    if user is None:
        user = get_random_user()

    builder = (
        Context.builder(user["key"])
        .name(user["name"])
        .set("email", user["email"])
    )

    for attr in ["plan", "role", "metro", "country"]:
        if attr in user:
            builder.set(attr, user[attr])

    return builder.build()


def get_user_by_key(key: str) -> dict:
    """Get a specific user by key. Falls back to generating a new user."""
    # Check static personas for backward compat
    for user in USER_PERSONAS:
        if user["key"] == key:
            return user
    # Dynamic keys won't be in the static list — return a fresh user
    return get_random_user()
