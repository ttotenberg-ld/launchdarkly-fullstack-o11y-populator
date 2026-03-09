"""
User generation for LaunchDarkly Observability Demo sessions.

Generates unique users with UUID-based keys, Faker-generated names, and
LD-themed email domains.  Every call to get_random_user() produces a
virtually unique identity that flows consistently through the stack:
simulator → frontend → backend.
"""

import random
import uuid

from faker import Faker
from ldclient import Context

# Seeded separately from the global random so user generation is
# reproducible within a process but still unique across processes.
_fake = Faker()
Faker.seed(None)  # entropy-seeded so each container gets different names

# Attribute pools — match the frontend's api.js lists exactly
PLANS = ['free', 'silver', 'gold', 'platinum', 'diamond']
ROLES = ['reader', 'writer', 'admin']
METROS = ['New York', 'Chicago', 'Minneapolis', 'Atlanta',
          'Los Angeles', 'San Francisco', 'Denver', 'Boston']
COUNTRIES = ['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP', 'BR', 'IN', 'MX']

# LaunchDarkly-punny email domains for flavor
_LD_DOMAINS = [
    'launchdarkly.demo',
    'darklylaunch.com',
    'lunchdarkly.net',
    'launchdorkly.io',
    'dimlylaunch.com',
    'launchbrightly.io',
    'toggledarkly.com',
    'flaglaunchly.io',
    'rolldarkly.net',
    'launchsoftly.io',
    'launchquickly.io',
    'lightlylaunch.net',
    'launchsnarkly.com',
    'launchdimly.io',
    'darklaunchery.net',
    'launchduskly.com',
    'dawnlaunchly.io',
    'launchdaily.net',
    'featureflagly.com',
    'staylightly.io',
    'rolloutdark.com',
    'nightlaunch.io',
    'flaganddark.com',
    'launchlightly.dev',
    'darktoggle.net',
    'switchdarkly.com',
    'launchnebula.io',
    'starlaunchly.com',
    'moonlightflag.io',
    'twilightlaunch.dev',
]

# Backward-compatible static personas (deprecated — use get_random_user())
USER_PERSONAS = [
    {
        "key": f"usr_{i + 1:03d}",
        "name": _fake.unique.name(),
        "email": f"{_fake.unique.user_name()}@{random.choice(_LD_DOMAINS)}",
    }
    for i in range(20)
]


def get_random_user() -> dict:
    """
    Generate a user with a unique UUID key, Faker name, and LD-themed email.

    Each call produces a fresh user identity that matches the attribute
    schema expected by the frontend (plan, role, metro, country) and
    is consistent across the full request chain.
    """
    first = _fake.first_name()
    last = _fake.last_name()
    name = f"{first} {last}"
    # Build a username slug:  lowercase first + last-initial + short random
    slug = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}"
    domain = random.choice(_LD_DOMAINS)

    return {
        "key": f"usr-{uuid.uuid4()}",
        "name": name,
        "email": f"{slug}@{domain}",
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
