# ♥♥─── API Client Mixins Initialization ─────────────────────────────────────────
from __future__ import annotations

from .tag_mixin import TagMixin, TagOperationError
from .task_mixin import TaskMixin, TaskOperationError
from .user_mixin import UserMixin, UserOperationError
from .inbox_mixin import InboxMixin, InboxOperationError
from .party_mixin import PartyMixin, PartyOperationError
from .paginate_mixin import (
    InboxPaginationMixin,
    ChallengePaginationMixin,
    BasePaginationUtilitiesMixin,
)
from .challenge_mixin import ChallengeMixin, ChallengeOperationError


__all__ = [
    "BasePaginationUtilitiesMixin",
    "ChallengeMixin",
    "ChallengeOperationError",
    "ChallengePaginationMixin",
    "InboxMixin",
    "InboxOperationError",
    "InboxPaginationMixin",
    "PartyMixin",
    "PartyOperationError",
    "TagMixin",
    "TagOperationError",
    "TaskMixin",
    "TaskOperationError",
    "UserMixin",
    "UserOperationError",
]
