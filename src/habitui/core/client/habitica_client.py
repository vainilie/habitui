# ♥♥─── Habitica Client ──────────────────────────────────────────────────────────
"""Define the main `HabiticaClient` class, which integrates all API functionalities."""

from __future__ import annotations

from typing import Any

from habitui.custom_logger import log

from .habitica_api import HabiticaAPI
from .mixin.tag_mixin import TagMixin
from .mixin.task_mixin import TaskMixin
from .mixin.user_mixin import UserMixin
from .mixin.inbox_mixin import InboxMixin
from .mixin.party_mixin import PartyMixin
from .mixin.paginate_mixin import InboxPaginationMixin, ChallengePaginationMixin
from .mixin.challenge_mixin import ChallengeMixin


class HabiticaClient(
    HabiticaAPI,
    ChallengeMixin,
    InboxMixin,
    PartyMixin,
    TagMixin,
    TaskMixin,
    UserMixin,
    ChallengePaginationMixin,
    InboxPaginationMixin,
):
    """A comprehensive, asynchronous Habitica API Client."""

    def __init__(self, config_override: Any | None = None) -> None:
        """Initialize the full HabiticaClient.

        :param config_override: Optional configuration object to override `application_settings.api`.
        """
        super().__init__(config_override=config_override)

        log.debug("HabiticaClient fully initialized with all mixins.")
