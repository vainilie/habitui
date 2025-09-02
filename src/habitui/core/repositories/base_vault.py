# ♥♥─── Generic Vault ────────────────────────────────────────────────────────────
from __future__ import annotations

from abc import ABC, abstractmethod
import math
from typing import TYPE_CHECKING, Any, Literal, TypeVar, ClassVar, Protocol, cast
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, func, select
from sqlalchemy import or_, event, delete, create_engine
from sqlalchemy.orm import object_session

from habitui.ui import icons
from habitui.core.models import ContentMetadata, HabiTuiSQLModel
from habitui.custom_logger import log
from habitui.config.app_config import app_config


if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy.engine import Engine
T_Model = TypeVar("T_Model", bound=HabiTuiSQLModel)
T_Collection = TypeVar("T_Collection")
SaveStrategy = Literal["smart", "force_recreate"]
DATABASE_FILE_NAME = app_config.storage.get_database_file_path()


class PositionableModel(Protocol):
    """Protocol for models that have a 'position' field."""

    position: int


# ─── Base Vault ───────────────────────────────────────────────────────────────
def _get_next_available_position(session: Session, model_cls: type[PositionableModel]) -> int:
    """Get the next available sequential position for a new item.

    :param session: The active database session.
    :param model_cls: The positionable SQLModel class.
    :returns: The next available position.
    """
    stmt = select(func.max(col(model_cls.position)))
    max_pos = session.exec(stmt).one()
    return (max_pos or 0) + 1


def _normalize_datetime_fields[T_Model: HabiTuiSQLModel](item: T_Model) -> T_Model:
    """Normalize all datetime fields of the model to UTC before merging.

    :param item: The model instance whose datetime fields need normalization.
    :returns: A new model instance with normalized datetime fields (UTC timezone-aware).
    """
    item_dict = item.model_dump()
    for field_name, field_value in item_dict.items():
        if isinstance(field_value, datetime):
            # Normalize to UTC and truncate microseconds for consistent storage
            if field_value.tzinfo is None:
                item_dict[field_name] = field_value.replace(tzinfo=UTC, microsecond=0)
            else:
                item_dict[field_name] = field_value.astimezone(UTC).replace(microsecond=0)
    return type(item)(**item_dict)


def _print_detailed_diff(existing_dict: dict[str, Any], new_dict: dict[str, Any], item_id: Any) -> None:
    """Print a detailed field-by-field comparison between two models.

    :param existing_dict: Dictionary of the existing model's attributes.
    :param new_dict: Dictionary of the new model's attributes.
    :param item_id: The ID of the item being compared.
    """
    log.debug(f"Differences for item with id = {item_id}")
    log.debug("{:<15} | {:<20} | {:<20}", "FIELD", "DB VALUE", "NEW VALUE")
    all_keys = sorted(existing_dict.keys() | new_dict.keys())
    for key in all_keys:
        existing_val = existing_dict.get(key)
        new_val = new_dict.get(key)
        if existing_val != new_val:
            log.debug("{:<15} | {:<20}({}) | {:<20} ({})", key, str(existing_val), type(existing_val).__name__, str(new_val), type(new_val).__name__)


def _item_has_changed(existing: HabiTuiSQLModel, new: HabiTuiSQLModel, debug: bool = True) -> bool:
    """Compare two models, returning True if their data differs.

    :param existing: The existing model instance.
    :param new: The new model instance.
    :param debug: If True, prints detailed differences.
    :returns: True if models differ, False otherwise.
    """

    def normalize_value(val: Any) -> Any:
        if isinstance(val, datetime):
            return val.replace(tzinfo=UTC) if val.tzinfo is None else val.astimezone(UTC)
        return val

    def are_floats_close(a: float, b: float) -> bool:
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)

    existing_dict = existing.model_dump()
    new_dict = new.model_dump()
    comp_existing = {}
    comp_new = {}
    all_keys = set(existing_dict) | set(new_dict)
    for key in all_keys:
        val_existing = existing_dict.get(key)
        val_new = new_dict.get(key)
        if isinstance(val_existing, datetime) and isinstance(val_new, datetime):
            val_existing = normalize_value(val_existing)
            val_new = normalize_value(val_new)
        elif isinstance(val_existing, float) and isinstance(val_new, float):
            if are_floats_close(val_existing, val_new):
                val_new = val_existing
        comp_existing[key] = val_existing
        comp_new[key] = val_new
    changed = comp_existing != comp_new
    if changed and debug:
        _print_detailed_diff(comp_existing, comp_new, existing.id)
    return changed


def _item_has_changed_after_merge(merged_item: T_Model, original_item: T_Model, debug: bool = False) -> bool:
    """Check if SQLAlchemy's `merge()` operation actually resulted in changes.

    SQLAlchemy's `merge()` is intelligent and only updates if there are
    real changes. This method prioritizes checking the session's
    modification state. If the session is not available or `is_modified`
    is not present, it falls back to a manual comparison using
    `_item_has_changed`.
    :param merged_item: The item after being merged into the session.
    :param original_item: The item before merging (used for fallback comparison).
    :param debug: If True, enables detailed diff logging in fallback comparison.
    :returns: True if the item was modified, False otherwise.
    """
    session = object_session(merged_item)
    if session and hasattr(session, "is_modified"):
        return session.is_modified(merged_item)
    # Fallback to manual comparison if session.is_modified is not available
    return _item_has_changed(merged_item, original_item, debug)


def _normalize_model_for_comparison(item: HabiTuiSQLModel) -> dict[str, Any]:
    """Normalize a model for comparison.

    :param item: The model instance to normalize.
    :returns: A dictionary representation of the normalized model.
    """
    item_dict = item.model_dump()
    normalized = {}
    for key, value in item_dict.items():
        if isinstance(value, datetime):
            # Normalize to UTC and truncate microseconds to avoid precision issues
            if value.tzinfo is None:
                normalized[key] = value.replace(tzinfo=UTC, microsecond=0)
            else:
                normalized[key] = value.astimezone(UTC).replace(microsecond=0)
        elif isinstance(value, float):
            normalized[key] = round(value, 9)
        else:
            normalized[key] = value
    return normalized


def _models_are_equivalent(model1: T_Model, model2: T_Model) -> bool:
    """Compare two models for equivalence.

    :param model1: The first model.
    :param model2: The second model.
    :returns: True if the models are equivalent, False otherwise.
    """
    norm1 = _normalize_model_for_comparison(model1)
    norm2 = _normalize_model_for_comparison(model2)
    # Perform explicit field-by-field comparison to ensure consistency with logging
    all_keys = set(norm1.keys()) | set(norm2.keys())
    return all(norm1.get(key) == norm2.get(key) for key in all_keys)  # No differences found


def _log_model_differences(existing: T_Model, new: T_Model) -> None:
    """Log specific differences between two models for debugging.

    :param existing: The existing model instance.
    :param new: The new model instance.
    """
    existing_norm = _normalize_model_for_comparison(existing)
    new_norm = _normalize_model_for_comparison(new)
    differences = []
    all_keys = set(existing_norm.keys()) | set(new_norm.keys())
    for key in all_keys:
        old_val = existing_norm.get(key)
        new_val = new_norm.get(key)
        if old_val != new_val:
            if isinstance(old_val, datetime) and isinstance(new_val, datetime):
                differences.append(f"{key}: {old_val.isoformat()} -> {new_val.isoformat()}")
            else:
                differences.append(f"{key}: {old_val} -> {new_val}")
    # Always log detailed differences if debug is enabled, even if normalized values are the same
    # This helps debug subtle differences not caught by normalization
    log.debug(f"Detailed differences for item with id = {existing.id}")
    log.debug("{:<15} | {:<20} | {:<20}", "FIELD", "DB VALUE", "NEW VALUE")
    all_keys = sorted(existing_norm.keys() | new_norm.keys())
    for key in all_keys:
        old_val = existing_norm.get(key)
        new_val = new_norm.get(key)
        # if old_val != new_val:
        log.debug("{:<15} | {:<20}({}) | {:<20} ({})", key, str(old_val), type(old_val).__name__, str(new_val), type(new_val).__name__)


class BaseVault[T_Collection](ABC):
    """Base class for vault implementations, providing common database operations.

    :param vault_name: The name of this vault instance.
    :param cache_time: Default cache time for the vault in timedelta.
    :param db_url: The database connection URL.
    :param echo: If True, SQLAlchemy will log all generated SQL.
    :ivar engine: The SQLAlchemy engine for database connections.
    :ivar vault_name: The name of this vault instance.
    :ivar timeout: The cache time for the vault in timedelta.
    :cvar ARCHIVE_POSITION_START: Default position for archived items.
    """

    ARCHIVE_POSITION_START: ClassVar[int] = 10_000

    def __init__(self, vault_name: str, cache_time: timedelta, db_url: str = f"sqlite:///{DATABASE_FILE_NAME}", echo: bool = True) -> None:
        """Initialize the database engine and create tables if they don't exist."""
        self.engine: Engine = create_engine(db_url, echo=echo)
        self.vault_name: str = vault_name
        self.timeout: timedelta = cache_time
        HabiTuiSQLModel.metadata.create_all(self.engine)
        self._configure_datetime_handling()
        log.debug(f"[i]{vault_name} vault[/i] initialized {icons.HISTORY}{cache_time}")

    def _initialize_vault_metadata(self) -> None:
        """Ensure database tables are ready for the vault."""
        log.debug(f"Database tables ready for {self.vault_name} vault ")

    def _update_vault_metadata(self, session: Session) -> None:
        """Update the vault-level metadata timestamp.

        :param session: The active database session.
        """
        vault_metadata = ContentMetadata(type=self.vault_name, last_fetched_at=datetime.now(UTC))
        session.merge(vault_metadata)
        log.debug(f"Updated vault-level metadata for {self.vault_name}")

    @abstractmethod
    def save(self, content: T_Collection, strategy: SaveStrategy = "smart", append_mode: bool = False, debug: bool = False) -> None:
        """Save a collection of content to the database.

        :param content: The content to save.
        :param strategy: "smart" (sync with changes) or "force_recreate" (delete all + insert).
        :param append_mode: If True, don't delete existing items not in new data (incremental).
        :param debug: Enable detailed logging.
        """

    @abstractmethod
    def load(self) -> T_Collection:
        """Load a collection of content from the database.

        :returns: The loaded collection of content.
        """

    @abstractmethod
    def get_model_configs(self) -> dict[str, type[HabiTuiSQLModel]]:
        """Return a mapping of content names to their SQLModel classes.

        :returns: A dictionary mapping content names to SQLModel classes.
        """

    def get_paginated(self, model_cls: type[T_Model], page: int = 1, per_page: int = 50, order_by: str = "id") -> tuple[list[T_Model], int]:
        """Retrieve paginated records for a given model.

        :param model_cls: The SQLModel class to query.
        :param page: The page number to retrieve (1-indexed).
        :param per_page: The number of items per page.
        :param order_by: The attribute to sort the results by.
        :returns: A tuple containing the list of items for the page and the total count.
        """
        with Session(self.engine) as session:  # type: ignore
            stmt_count = select(func.count(col(model_cls.id)))
            total = session.exec(stmt_count).one()
            order_column = getattr(model_cls, order_by, col(model_cls.id))
            offset = (page - 1) * per_page
            query = select(model_cls).order_by(order_column).offset(offset).limit(per_page)
            items = list(session.exec(query).all())
            return items, total

    def get_filtered(self, model_cls: type[T_Model], filters: dict[str, Any], limit: int = 100) -> list[T_Model]:
        """Retrieve records matching a set of filters.

        :param model_cls: The SQLModel class to query.
        :param filters: A dictionary of field names and values to filter by.
        :param limit: The maximum number of records to return.
        :returns: A list of matching items.
        """
        with Session(self.engine) as session:  # type: ignore
            query = select(model_cls)
            for field, value in filters.items():
                if hasattr(model_cls, field):
                    column = col(getattr(model_cls, field))
                    query = query.where(column.icontains(value)) if isinstance(value, str) else query.where(column == value)
            return list(session.exec(query.limit(limit)).all())

    def get_by_id(self, model_cls: type[T_Model], item_id: Any) -> T_Model | None:
        """Retrieve a single item by its primary key (id).

        :param model_cls: The SQLModel class to query.
        :param item_id: The ID of the item to retrieve.
        :returns: The found item or None if not found.
        """
        with Session(self.engine) as session:  # type: ignore
            return session.get(model_cls, item_id)

    def exists(self, model_cls: type[T_Model], item_id: Any) -> bool:
        """Check if an item with the given primary key (id) exists.

        :param model_cls: The SQLModel class to query.
        :param item_id: The ID of the item to check for existence.
        :returns: True if the item exists, False otherwise.
        """
        with Session(self.engine) as session:  # type: ignore
            stmt = select(col(model_cls.id)).where(col(model_cls.id) == item_id)
            result = session.exec(stmt).first()
            return result is not None

    def count(self, model_cls: type[T_Model]) -> int:
        """Return the total number of records for a model.

        :param model_cls: The SQLModel class to count.
        :returns: The total number of records.
        """
        with Session(self.engine) as session:  # type: ignore
            stmt = select(func.count(col(model_cls.id)))
            return session.exec(stmt).one()

    @staticmethod
    def _is_positionable(model_cls: type[Any]) -> bool:
        """Check if a model conforms to the PositionableModel protocol.

        :param model_cls: The model class to check.
        :returns: True if the model has a 'position' attribute, False otherwise.
        """
        return hasattr(model_cls, "position")

    def _get_next_archive_position(self, session: Session, model_cls: type[PositionableModel]) -> int:
        """Get the starting position for newly archived items.

        :param session: The active database session.
        :param model_cls: The positionable SQLModel class.
        :returns: The next available archive position.
        """
        stmt = select(func.max(col(model_cls.position)))
        max_pos = session.exec(stmt).one()
        return max(self.ARCHIVE_POSITION_START, (max_pos or 0) + 1)

    @staticmethod
    def _update_metadata(session: Session, name: str) -> None:
        """Upsert the metadata record for a given content type.

        :param session: The active database session.
        :param name: The name of the content type.
        """
        metadata = ContentMetadata(type=name, last_fetched_at=datetime.now(UTC))
        session.merge(metadata)

    def _save_single_item(self, session: Session, model_cls: type[T_Model], item: T_Model, strategy: SaveStrategy, content_name: str, debug: bool = False) -> None:  # noqa: PLR0917
        """Save a single item using the specified strategy.

        :param session: The active database session.
        :param model_cls: The SQLModel class of the item.
        :param item: The item to save.
        :param strategy: "smart" (sync with changes) or "force_recreate" (delete all + insert).
        :param content_name: The descriptive name for the content type (for logging).
        :param debug: Enable detailed logging.
        """
        if strategy == "force_recreate":
            stmt = delete(model_cls)
            session.exec(stmt)  # type: ignore
            session.flush()
            session.add(item)
            log.info(f"{icons.ERASE}{content_name.capitalize()} sync: Recreated table with 1 item")
        else:
            existing_item = session.get(model_cls, item.id)  # type: ignore
            if existing_item is None:
                session.add(item)
                log.info(f"{content_name.capitalize()}: {icons.CREATE}1")
            elif _item_has_changed(existing_item, item, debug):
                self._update_item_fields(existing_item, item)
                log.info(f"{content_name.capitalize()}: {icons.RELOAD}1")
            else:
                log.info(f"{content_name.capitalize()}: {icons.CHECK}")
        self._update_metadata(session, content_name)
        self._update_vault_metadata(session)

    def _save_item_list(self, session: Session, model_cls: type[T_Model], items: Iterable[T_Model], strategy: SaveStrategy, content_name: str, debug: bool = False, use_archiving: bool = False, append_mode: bool = False) -> None:  # noqa: PLR0917
        """Dispatch to the correct save method based on the chosen strategy.

        :param session: The active database session.
        :param model_cls: The SQLModel class to save.
        :param items: An iterable of model instances to save.
        :param strategy: The save strategy to use.
        :param content_name: The descriptive name for the content type (for logging).
        :param debug: If True, enables detailed diff logging.
        :param use_archiving: If True, obsolete items are archived instead of deleted.
        :param append_mode: If True, existing items not in new data are preserved.
        """
        item_list = list(items)
        is_positionable = self._is_positionable(model_cls)
        log.debug("Strategy: {}", strategy)
        if strategy == "force_recreate":
            self._force_recreate_save(session, model_cls, item_list, content_name)
        elif append_mode:
            self._save_append_mode(session, model_cls, item_list, content_name, debug)
        else:
            self._save_full_sync(session, model_cls, item_list, content_name, debug, use_archiving and is_positionable)
        self._update_vault_metadata(session)

    def _save_full_sync(self, session: Session, model_cls: type[T_Model], items: list[T_Model], name: str, debug: bool, use_archiving: bool) -> None:  # noqa: PLR0917
        """Synchronize a list of items with the database.

        :param session: The active database session.
        :param model_cls: The SQLModel class of the items.
        :param items: The list of items to sync.
        :param name: The descriptive name for the content type (for logging).
        :param debug: If True, enables detailed diff logging.
        :param use_archiving: If True, obsolete items are archived instead of deleted.
        """
        stmt = select(model_cls)
        existing_items_list = list(session.exec(stmt).all())
        existing_items = {item.id: item for item in existing_items_list}
        created, updated, unchanged = 0, 0, 0
        new_ids = set()
        for item in items:
            new_ids.add(item.id)
            existing_item = existing_items.get(item.id)
            normalized_item = _normalize_datetime_fields(item)
            if existing_item is None:
                session.add(normalized_item)
                created += 1
            elif _models_are_equivalent(existing_item, normalized_item):
                unchanged += 1
                if debug:
                    log.debug(f"Item {item.id} unchanged, skipping update")
            else:
                session.merge(normalized_item)
                updated += 1
                if debug:
                    log.debug(f"Item {item.id} changed, updating")
                    _log_model_differences(existing_item, normalized_item)
        obsolete_ids = set(existing_items.keys()) - new_ids
        archived_or_deleted = 0
        if obsolete_ids:
            if use_archiving:
                positionable_model_cls = cast("type[PositionableModel]", model_cls)
                positionable_existing_map = cast("dict[Any, PositionableModel]", existing_items)
                self._archive_items(session, positionable_model_cls, obsolete_ids, positionable_existing_map)
                archived_or_deleted = len(obsolete_ids)
                action = icons.ARCHIVE
            else:
                stmt_delete = delete(model_cls).where(col(model_cls.id).in_(obsolete_ids))
                session.exec(stmt_delete)  # type: ignore
                archived_or_deleted = len(obsolete_ids)
                action = icons.ERASE
        if debug or created > 0 or updated > 0 or archived_or_deleted > 0:
            log.info(f"{icons.CLIP}{name.capitalize()}: {icons.CREATE}{created} {icons.RELOAD}{updated} {icons.APROX}{unchanged} {action if archived_or_deleted > 0 else ''}{archived_or_deleted if archived_or_deleted > 0 else ''}")
        else:
            log.info(f"[b]{icons.CHECK}{name.capitalize()}[/]")
        self._update_metadata(session, name)

    def _save_append_mode(self, session: Session, model_cls: type[T_Model], items: list[T_Model], name: str, debug: bool) -> None:  # noqa: ARG002
        """Save items in append mode.

        :param session: The active database session.
        :param model_cls: The SQLModel class of the items.
        :param items: The list of items to save.
        :param name: The descriptive name for the content type (for logging).
        :param debug: If True, enables detailed diff logging.
        """
        if not items:
            return
        created, updated, unchanged = 0, 0, 0
        new_ids = {item.id for item in items}
        stmt = select(model_cls).where(col(model_cls.id).in_(new_ids))
        existing_items = {item.id: item for item in session.exec(stmt).all()}
        for item in items:
            existing_item = existing_items.get(item.id)
            if existing_item is None:
                if self._is_positionable(model_cls):
                    positionable_item = cast("PositionableModel", item)
                    if not hasattr(positionable_item, "position") or positionable_item.position is None:
                        positionable_model_cls = cast("type[PositionableModel]", model_cls)
                        positionable_item.position = _get_next_available_position(session, positionable_model_cls)
                normalized_item = _normalize_datetime_fields(item)
                session.add(normalized_item)
                created += 1
            elif _models_are_equivalent(existing_item, item):
                unchanged += 1
            else:
                normalized_item = _normalize_datetime_fields(item)
                session.merge(normalized_item)
                updated += 1
        log.info("{}{} append: {} created, {} updated, {} unchanged", icons.CLIP, name.capitalize(), created, updated, unchanged)
        self._update_metadata(session, name)

    def _force_recreate_save(self, session: Session, model_cls: type[T_Model], items: list[T_Model], name: str) -> None:
        """Delete all existing records for a model and add the new ones.

        :param session: The active database session.
        :param model_cls: The SQLModel class.
        :param items: The list of items to save.
        :param name: The descriptive name for the content type (for logging).
        """
        with session.no_autoflush:  # type: ignore
            log.warning("Force-recreating table '{}', all data will be lost.", model_cls.__tablename__)
            stmt = delete(model_cls)
            session.exec(stmt)  # type: ignore
            session.flush()
            session.commit()
            session.add_all(items)
        self._update_metadata(session, name)
        log.info("{} {} sync:\n •  Recreated table with {} items.", icons.RELOAD, name.capitalize(), len(items))

    def _archive_items(self, session: Session, model_cls: type[PositionableModel], ids_to_archive: set[Any], existing_items_map: dict[Any, PositionableModel]) -> None:
        """Assign archive positions to a set of items.

        :param session: The active database session.
        :param model_cls: The positionable SQLModel class.
        :param ids_to_archive: A set of IDs of items to archive.
        :param existing_items_map: A dictionary mapping existing item IDs to their instances.
        """
        next_pos = self._get_next_archive_position(session, model_cls)
        for i, item_id in enumerate(ids_to_archive):
            item = existing_items_map.get(item_id)
            if item is not None:
                item.position = next_pos + i
        session.flush()

    @staticmethod
    def _update_item_fields(existing: HabiTuiSQLModel, new: HabiTuiSQLModel) -> None:
        """Update fields of an existing model from a new model instance.

        :param existing: The existing model to update.
        :param new: The new model with updated values.
        """
        for key, value in new.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)

    def _configure_datetime_handling(self) -> None:
        """Configure the engine to handle datetime, especially for SQLite."""

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:  # noqa: ARG001
            if "sqlite" in str(self.engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA timezone = 'UTC'")
                cursor.close()

    def search(self, model_cls: type[T_Model], term: str, fields: list[str] | None = None, limit: int = 10) -> list[T_Model]:
        """Perform a generic search across specified text-like fields.

        :param model_cls: The SQLModel class to search.
        :param term: The search term.
        :param fields: A list of field names to search within. Defaults to common text fields.
        :param limit: The maximum number of results to return.
        :returns: A list of matching items.
        """
        with Session(self.engine) as session:  # type: ignore
            search_fields = fields or ["text", "notes", "name", "description"]
            conditions = [col(getattr(model_cls, field)).icontains(term) for field in search_fields if hasattr(model_cls, field)]
            if not conditions:
                return []
            stmt = select(model_cls).where(or_(*conditions)).limit(limit)
            return list(session.exec(stmt).all())

    def get_stats(self) -> dict[str, int]:
        """Return record counts for all configured model types.

        :returns: A dictionary where keys are content type names suffixed with '_count' and values are the counts.
        """
        with Session(self.engine) as session:  # type: ignore
            stats = {}
            for name, model_cls in self.get_model_configs().items():
                stmt = select(func.count(col(model_cls.id)))
                count = session.exec(stmt).one()
                stats[f"{name}_count"] = count
            return stats

    def get_metadata(self, content_type: str) -> ContentMetadata | None:
        """Retrieve metadata for a specific content type.

        :param content_type: The type of content to retrieve metadata for.
        :returns: The ContentMetadata object or None if not found.
        """
        with Session(self.engine) as session:  # type: ignore
            return session.get(ContentMetadata, content_type)

    def get_vault_metadata(self) -> ContentMetadata | None:
        """Retrieve vault-level metadata.

        :returns: The ContentMetadata object for the vault or None if not found.
        """
        return self.get_metadata(self.vault_name)

    def get_vault_last_updated(self) -> datetime | None:
        """Get the timestamp of the last vault-level update.

        :returns: The datetime of the last update, or None if no vault metadata exists.
        """
        vault_metadata = self.get_vault_metadata()
        return vault_metadata.last_fetched_at if vault_metadata else None

    def is_vault_fresh(self) -> bool:
        """Check if the vault data is considered fresh based on its `cache_time`.

        :returns: True if the vault is fresh and contains data, False otherwise.
        """
        vault_metadata = self.get_vault_metadata()
        if vault_metadata is None or vault_metadata.last_fetched_at is None:
            log.debug(f"{self.vault_name} vault has no metadata - not fresh")
            return False
        stats = self.get_stats()
        total_records = sum(count for key, count in stats.items() if key.endswith("_count"))
        if total_records == 0:
            log.debug(f"{self.vault_name} vault has metadata but no records - not fresh")
            return False
        now_utc = datetime.now(UTC)
        last_fetched = vault_metadata.last_fetched_at
        last_fetched = last_fetched.replace(tzinfo=UTC) if last_fetched.tzinfo is None else last_fetched.astimezone(UTC)
        cutoff_time = now_utc - self.timeout
        is_fresh = last_fetched > cutoff_time
        log.debug("Vault freshness check:\n {} last_fetched={} \n • cutoff={}\n • fresh={}", last_fetched, cutoff_time, is_fresh)
        return is_fresh

    def get_vault_age(self) -> timedelta | None:
        """Get the age of the entire vault.

        :returns: The age as a timedelta, or None if no vault metadata exists.
        """
        vault_metadata = self.get_vault_metadata()
        if vault_metadata is None or vault_metadata.last_fetched_at is None:
            return None
        now_utc = datetime.now(UTC)
        last_fetched = vault_metadata.last_fetched_at
        last_fetched = last_fetched.replace(tzinfo=UTC) if last_fetched.tzinfo is None else last_fetched.astimezone(UTC)
        return now_utc - last_fetched

    def inspect_data(self) -> None:
        """Print a comprehensive data inspection report to the console."""
        log.info("Content Database Inspection")
        log.info(f"Vault Name: {self.vault_name}")
        vault_metadata = self.get_vault_metadata()
        if vault_metadata:
            vault_age = self.get_vault_age()
            log.info(f"Vault {icons.HISTORY}: {vault_metadata.last_fetched_at} ({vault_age})")
            log.info("Vault is fresh: {}", icons.CHECK if self.is_vault_fresh() else icons.ERROR)
        stats = self.get_stats()
        log.info(f"{icons.CHART}Record Counts:")
        for key, count in stats.items():
            log.info(" {}: {}", key.replace("_", " ").capitalize(), count)
        self.validate_data_integrity()

    def validate_data_integrity(self) -> list[str]:
        """Perform basic integrity checks, such as for empty IDs and duplicates.

        :returns: A list of issues found. Empty if no issues.
        """
        log.debug("Performing data integrity check...")
        issues: list[str] = []
        with Session(self.engine) as session:  # type: ignore
            for name, model_cls in self.get_model_configs().items():
                stmt_invalid_ids = select(model_cls).where(or_(col(model_cls.id).is_(None), col(model_cls.id) == ""))  # noqa: PLC1901
                invalid_items = list(session.exec(stmt_invalid_ids).all())
                if invalid_items:
                    issues.append(f"[{name}] Found {len(invalid_items)} items with empty/null IDs")
                stmt_duplicates = select(col(model_cls.id), func.count(col(model_cls.id))).group_by(col(model_cls.id)).having(func.count(col(model_cls.id)) > 1)
                duplicates = list(session.exec(stmt_duplicates).all())
                if duplicates:
                    issues.append(f"[{name}] Found {len(duplicates)} duplicate IDs")
                if self._is_positionable(model_cls):
                    positionable_model = cast("type[PositionableModel]", model_cls)
                    stmt_null_positions = select(positionable_model).where(col(positionable_model.position).is_(None))
                    null_positions = list(session.exec(stmt_null_positions).all())
                    if null_positions:
                        issues.append(f"[{name}] Found {len(null_positions)} items with null positions")
        if issues:
            log.warning("Data integrity check found {} issues", len(issues))
            for issue in issues:
                log.warning(f"{icons.SMALL_SQUARE}{issue}")
        else:
            log.debug("Data integrity check passed")
        return issues

    def is_vault_ready_for_load(self) -> tuple[bool, list[str]]:
        """Verify if the vault is ready for safe loading. Checks for data presence, freshness, and integrity.

        :returns: A tuple containing:
                - True if the vault is ready for load, False otherwise.
                - A list of issues found (empty if `is_ready` is True).
        """
        issues = []
        # 1. Check if there is data in the vault
        stats = self.get_stats()
        total_records = sum(count for key, count in stats.items() if key.endswith("_count"))
        if total_records == 0:
            issues.append("Vault is empty")
        # 2. Check data freshness
        if not self.is_vault_fresh():
            vault_age = self.get_vault_age()
            if vault_age:
                issues.append(f"{icons.HISTORY}{self.timeout} ({vault_age})")
            else:
                issues.append("Vault metadata is missing or corrupted")
        # 3. Check data integrity
        integrity_issues = self.validate_data_integrity()
        if integrity_issues:
            issues.extend(integrity_issues[:5])  # Limit to 5 for brevity in summary
        # 4. Check for vault metadata existence
        vault_metadata = self.get_vault_metadata()
        if not vault_metadata:
            issues.append("Vault metadata is missing")
        is_ready = len(issues) == 0
        if is_ready:
            log.success(f"{self.vault_name} vault is ready {icons.SMALL_SQUARE}({total_records} items)")
        else:
            log.warning(f"{self.vault_name} vault has {len(issues)} issues")
            for issue in issues:
                log.warning("    {} {}", icons.SMALL_SQUARE, issue)
        return is_ready, issues

    @staticmethod
    def validate_datetime_fields_in_models(model_configs: dict[str, type[HabiTuiSQLModel]]) -> list[str]:
        """Validate that datetime fields in models are configured for timezone handling.

        :param model_configs: A dictionary mapping content names to their SQLModel classes.
        :returns: A list of warnings for datetime fields that might need better timezone configuration.
        """
        warnings = []
        for name, model_cls in model_configs.items():
            for field_name, field_info in model_cls.model_fields.items():
                if field_info.annotation and "datetime" in str(field_info.annotation) and not any("UTC" in str(constraint) for constraint in (field_info.json_schema_extra or {}).values() if isinstance(constraint, dict) and "tz" in constraint):
                    warnings.append(f"Model {name}.{field_name}: Consider using timezone-aware datetime (e.g., datetime with tzinfo=UTC or Pydantic's `AwareDatetime`)")
        return warnings
