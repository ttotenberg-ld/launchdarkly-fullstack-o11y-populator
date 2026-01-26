"""
User personas with LaunchDarkly-punny emails for demo sessions.
"""

import random
from ldclient import Context

# User personas with LaunchDarkly pun emails
USER_PERSONAS = [
    {"key": "usr_001", "name": "Luna Darksworth", "email": "luna@staylightly.io"},
    {"key": "usr_002", "name": "Lance Dimly", "email": "lance@darklaunchly.com"},
    {"key": "usr_003", "name": "Darcy Launch", "email": "darcy@lunchdarkly.net"},
    {"key": "usr_004", "name": "Larry Duskman", "email": "larry@launchdorkly.io"},
    {"key": "usr_005", "name": "Lydia Twilight", "email": "lydia@dimlylaunch.com"},
    {"key": "usr_006", "name": "Drake Moonson", "email": "drake@launchbrightly.io"},
    {"key": "usr_007", "name": "Dawn Flagworth", "email": "dawn@toggledarkly.com"},
    {"key": "usr_008", "name": "Felix Feature", "email": "felix@flaglaunchly.io"},
    {"key": "usr_009", "name": "Sage Rollout", "email": "sage@rolldarkly.net"},
    {"key": "usr_010", "name": "Nova Experiment", "email": "nova@launchsoftly.io"},
    {"key": "usr_011", "name": "River Toggle", "email": "river@darklylaunch.com"},
    {"key": "usr_012", "name": "Stella Variant", "email": "stella@launchquickly.io"},
    {"key": "usr_013", "name": "Atlas Segment", "email": "atlas@lightlylaunch.net"},
    {"key": "usr_014", "name": "Ivy Targeting", "email": "ivy@launchsnarkly.com"},
    {"key": "usr_015", "name": "Max Context", "email": "max@launchdimly.io"},
    {"key": "usr_016", "name": "Zara Percentage", "email": "zara@darklaunchery.net"},
    {"key": "usr_017", "name": "Quinn Prerequisite", "email": "quinn@launchduskly.com"},
    {"key": "usr_018", "name": "Blake Fallthrough", "email": "blake@dawnlaunchly.io"},
    {"key": "usr_019", "name": "Morgan Targeting", "email": "morgan@launchdaily.net"},
    {"key": "usr_020", "name": "Casey Killswitch", "email": "casey@featureflagly.com"},
]


def get_random_user() -> dict:
    """Get a random user persona."""
    return random.choice(USER_PERSONAS)


def get_user_context(user: dict = None) -> Context:
    """
    Create a LaunchDarkly context from a user persona.
    If no user is provided, selects a random one.
    """
    if user is None:
        user = get_random_user()
    
    return (
        Context.builder(user["key"])
        .name(user["name"])
        .set("email", user["email"])
        .build()
    )


def get_user_by_key(key: str) -> dict:
    """Get a specific user by key."""
    for user in USER_PERSONAS:
        if user["key"] == key:
            return user
    return get_random_user()
