"""SQLAlchemy model aggregator.

Importing this module ensures every ORM model is registered against
``Base.metadata`` before ``create_all`` runs. Feature subagents must add
their model module imports here.
"""

from app.features.auth.models import User  # noqa: F401
from app.features.tasks.models import Task, Subtask  # noqa: F401
