# ♥♥─── Tag Vault ────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, cast
from datetime import timedelta

from sqlmodel import Session, select

from habitui.custom_logger import log
from habitui.config.app_config import app_config
from habitui.core.models.tag_model import TagComplex, TagCollection

from .base_vault import DATABASE_FILE_NAME, BaseVault, SaveStrategy


if TYPE_CHECKING:
    from sqlalchemy.sql.expression import ColumnElement

    from habitui.core.models import HabiTuiSQLModel
TIMEOUT = timedelta(minutes=app_config.cache.live_minutes)


class TagVault(BaseVault[TagCollection]):
    """Vault implementation for managing tags and their collections."""

    def __init__(self, vault_name: str = "tag_vault", db_url: str | None = None, echo: bool = False) -> None:
        """Initialize the TagVault with the appropriate cache timeout.

        :param vault_name: The name of this vault instance.
        :param db_url: The database connection URL (uses default if None).
        :param echo: If True, SQLAlchemy will log all generated SQL.
        """
        if db_url is None:
            db_url = f"sqlite:///{DATABASE_FILE_NAME}"
        super().__init__(vault_name=vault_name, cache_time=TIMEOUT, db_url=db_url, echo=echo)

    def get_model_configs(self) -> dict[str, type[HabiTuiSQLModel]]:
        """Return the mapping of content types to their model classes for tags.

        :return: A dictionary mapping content type names to their SQLModel classes.
        """
        return {"tag": TagComplex}

    def save(self, content: TagCollection, strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Save tag content to the database using a specified strategy.

        :param content: A `TagCollection` object containing tags to be saved.
        :param strategy: The save strategy ('smart', 'incremental', 'force_recreate').
        :param debug: If True, enables detailed logging for changes during the save process.
        """
        with Session(self.engine) as session:  # type: ignore
            log.info("Starting tags database sync with '{}' strategy.", strategy)
            tags = content.tags
            if tags:
                self._save_item_list(session, TagComplex, tags, strategy, "tags", debug=debug)
            session.commit()
            log.info("Tags database sync completed.")

    def load(self) -> TagCollection:
        """Load all `TagComplex` objects from the database and reconstructs a `TagCollection`.

        :return: A `TagCollection` object containing all stored tags.
        """
        with Session(self.engine) as session:  # type: ignore
            position_col = cast("ColumnElement", TagComplex.position)
            tags_query = select(TagComplex).order_by(position_col)
            stored_tags = list(session.exec(tags_query).all())
            return TagCollection(tags=stored_tags)

    def inspect_data(self) -> None:
        """Print a comprehensive inspection report for tag data."""
        super().inspect_data()
        with Session(self.engine) as session:  # type: ignore
            log.info("TAGS INFO:")
            all_tags = session.exec(select(TagComplex)).all()
            if all_tags:
                for tag in all_tags:
                    log.info("  • ID: {} | Name: {} | Type: {} | Position: {}", tag.id, tag.name, tag.tag_type, tag.position)
            else:
                log.info("  • No tag data found.")
