# ♥♥─── Party Vault ────────────────────────────────────────────────────────────
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from sqlmodel import Session, select

from habitui.config.app_config import app_config
from habitui.core.models import HabiTuiSQLModel
from habitui.core.models.party_model import PartyChat, PartyCollection, PartyInfo
from habitui.custom_logger import log
from habitui.ui import icons

from .base_vault import DATABASE_FILE_NAME, BaseVault, SaveStrategy

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement


TIMEOUT = timedelta(minutes=app_config.cache.live_minutes)


# ─── Party Vault ──────────────────────────────────────────────────────────────
class PartyVault(BaseVault[PartyCollection]):
    """Vault implementation for managing party-related content."""

    def __init__(self, vault_name: str = "party_vault", db_url: str | None = None, echo: bool = False) -> None:
        """Initialize the PartyVault with the appropriate cache timeout.

        :param vault_name: The name of this vault instance.
        :param db_url: The database connection URL (uses default if None).
        :param echo: If True, SQLAlchemy will log all generated SQL.
        """
        if db_url is None:
            db_url = f"sqlite:///{DATABASE_FILE_NAME}"

        super().__init__(vault_name=vault_name, cache_time=TIMEOUT, db_url=db_url, echo=echo)

    def get_model_configs(self) -> dict[str, type[HabiTuiSQLModel]]:
        """Returns the mapping of content types to their model classes."""
        return {"party": PartyInfo, "chat": PartyChat}

    def save(self, content: PartyCollection, strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Saves party content to the database using a specified strategy.

        :param content: A PartyCollection object containing party info and chat
            messages.
        :param strategy: The save strategy ('smart', 'incremental',
            'force_recreate').
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:
            log.info("Starting database sync with '{}' strategy.", strategy)
            if content.party_info:
                self._save_single_item(session, PartyInfo, content.party_info, strategy, "party", debug)
            if content.party_chat:
                self._save_item_list(
                    session,
                    PartyChat,
                    content.party_chat,
                    strategy,
                    "chat",
                    debug=debug,
                    use_archiving=True,
                    append_mode=False,
                )
            session.commit()
            log.info("Database sync completed.")

    def save_recent_chats(
        self, recent_chats: list[PartyChat], strategy: SaveStrategy = "smart", debug: bool = False
    ) -> None:
        """Saves recent chats without affecting older, preserved chat messages.

        :param recent_chats: A list of new or updated chat messages.
        :param strategy: The save strategy to apply to the recent items.
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:
            self._save_item_list(session, PartyChat, recent_chats, strategy, "chat", debug=debug, append_mode=True)
            session.commit()

    def load(self) -> PartyCollection:
        """Loads all party content from the database.

        :return: A PartyCollection object containing party info and chat messages.
        """
        with Session(self.engine) as session:
            party_info = session.exec(select(PartyInfo)).first()
            position_col = cast("ColumnElement", PartyChat.position)
            chat_query = (
                select(PartyChat).where(PartyChat.position < self.ARCHIVE_POSITION_START).order_by(position_col)  # type: ignore
            )  # type: ignore
            party_chat = list(session.exec(chat_query).all())
            return PartyCollection(party_info=party_info, party_chat=party_chat)

    def get_active_chats(self, limit: int = 100) -> list[PartyChat]:
        """Retrieves active (non-archived) chat messages, ordered by position.

        :param limit: The maximum number of chats to return.
        :return: A list of active PartyChat messages.
        """
        with Session(self.engine) as session:
            position_col = cast("ColumnElement", PartyChat.position)
            query = (
                select(PartyChat)
                .where(PartyChat.position < self.ARCHIVE_POSITION_START)  # type: ignore
                .order_by(position_col)
                .limit(limit)
            )  # type: ignore
            return list(session.exec(query).all())

    def archive_chats_by_count(self, keep_count: int = 500) -> int:
        """Archives older chat messages, keeping only the most recent ones.

        :param keep_count: The number of recent chat messages to keep active.
        :return: The number of chat messages that were archived.
        """
        with Session(self.engine) as session:
            position_col = cast("ColumnElement", PartyChat.position)
            chats_to_archive = list(
                session.exec(
                    select(PartyChat)
                    .where(PartyChat.position < self.ARCHIVE_POSITION_START)  # type: ignore
                    .order_by(position_col.desc())
                    .offset(keep_count)
                ).all()
            )  # type: ignore
            if not chats_to_archive:
                log.info("No old chats found to archive.")
                return 0
            next_pos = self._get_next_archive_position(session, PartyChat)  # type: ignore
            for i, chat in enumerate(chats_to_archive):
                chat.position = next_pos + i
            session.commit()
            log.info("Archived {} old chat messages.", len(chats_to_archive))
            return len(chats_to_archive)

    def inspect_data(self) -> None:
        """Prints a comprehensive inspection report for party data."""
        super().inspect_data()
        with Session(self.engine) as session:
            log.info(f"\n{icons.GROUP} PARTY INFO:")
            party = session.exec(select(PartyInfo)).first()
            if party:
                log.info("  • Key: {} | Name: {}", party.id, getattr(party, "name", "N/A"))
            else:
                log.info("  • No party data found.")

            log.info(f"\n{icons.BUBBLE} ACTIVE CHATS (first 5):")
            for chat in self.get_active_chats(limit=5):
                text_preview = getattr(chat, "text", "")[:50]
                log.info("  • {} [pos: {}] {}...", chat.id, getattr(chat, "position", "N/A"), text_preview)
