# ♥♥─── API Client Mixins Initialization ─────────────────────────────────────────
from __future__ import annotations

from .challenge_mixin import ChallengeMixin, ChallengeOperationError
from .inbox_mixin import InboxMixin, InboxOperationError
from .paginate_mixin import BasePaginationUtilitiesMixin, ChallengePaginationMixin, InboxPaginationMixin
from .party_mixin import PartyMixin, PartyOperationError
from .tag_mixin import TagMixin, TagOperationError
from .task_mixin import TaskMixin, TaskOperationError
from .user_mixin import UserMixin, UserOperationError

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
