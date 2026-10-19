"""Fast, isolated settings for the focused test suite.

PostgreSQL remains the production database; run the tagged PostgreSQL tests
with ``config.settings`` against an isolated PostgreSQL database.
"""

from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
