# ♥♥─── Content Vault ────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import timedelta

from sqlmodel import Session, select

from habitui.ui import icons
from habitui.custom_logger import log
from habitui.config.app_config import app_config
from habitui.core.models.content_model import GearItem, QuestItem, SpellItem, ContentCollection

from .base_vault import DATABASE_FILE_NAME, BaseVault, SaveStrategy


if TYPE_CHECKING:
	from habitui.core.models import HabiTuiSQLModel


TIMEOUT = timedelta(days=app_config.cache.content_days)


class ContentVault(BaseVault[ContentCollection]):
	"""Manage storage and retrieval of game content."""

	def __init__(self, vault_name: str = "content_vault", db_url: str | None = None, echo: bool = False) -> None:
		"""Initialize the ContentVault with the appropriate cache timeout.

		:param vault_name: The name of this vault instance.
		:param db_url: The database connection URL (uses default if None).
		:param echo: If True, SQLAlchemy will log all generated SQL.
		"""
		if db_url is None:
			db_url = f"sqlite:///{DATABASE_FILE_NAME}"
		super().__init__(vault_name=vault_name, cache_time=TIMEOUT, db_url=db_url, echo=echo)

	def get_model_configs(self) -> dict[str, type[HabiTuiSQLModel]]:
		"""Return the mapping of content types to their model classes."""
		return {"gear": GearItem, "spells": SpellItem, "quests": QuestItem}

	def save(self, content: ContentCollection, strategy: SaveStrategy = "smart", debug: bool = False) -> None:
		"""Save all game content from a ContentCollection to the database.

		:param content: A ContentCollection object containing game data.
		:param strategy: The save strategy ('smart', 'incremental', 'force_recreate').
		:param debug: If True, enables detailed logging for changes.
		"""
		with Session(self.engine) as session:  # pyright: ignore[reportGeneralTypeIssues]
			log.info("Starting database sync with '{}' strategy.", strategy)
			content_map: dict[str, Any] = {
				"gear": content.gear.values(),
				"spells": content.spells.values(),
				"quests": content.quests.values(),
			}
			for name, model_cls in self.get_model_configs().items():
				items = content_map.get(name, [])
				if items:
					self._save_item_list(session, model_cls, items, strategy, name, debug)
			session.commit()
			log.info("Database sync completed.")

	def load(self) -> ContentCollection:
		"""Load all game content from the database into a ContentCollection."""
		with Session(self.engine) as session:  # pyright: ignore[reportGeneralTypeIssues]
			return ContentCollection(
				gear={item.key: item for item in session.exec(select(GearItem))},
				spells={item.key: item for item in session.exec(select(SpellItem))},
				quests={item.key: item for item in session.exec(select(QuestItem))},
			)

	def search_gear(self, term: str, limit: int = 10) -> list[GearItem]:
		"""Search for gear items by a given term.

		:param term: The search term.
		:param limit: The maximum number of results to return.
		:return: A list of matching GearItem objects.
		"""
		return self.search(GearItem, term, limit=limit)

	def search_quests(self, term: str, limit: int = 10) -> list[QuestItem]:
		"""Search for quest items by a given term.

		:param term: The search term.
		:param limit: The maximum number of results to return.
		:return: A list of matching QuestItem objects.
		"""
		return self.search(QuestItem, term, limit=limit)

	def search_spells(self, term: str, limit: int = 10) -> list[SpellItem]:
		"""Search for spell items by a given term.

		:param term: The search term.
		:param limit: The maximum number of results to return.
		:return: A list of matching SpellItem objects.
		"""
		return self.search(SpellItem, term, limit=limit)

	def inspect_data(self) -> None:
		"""Print a comprehensive inspection report for all game content."""
		super().inspect_data()
		with Session(self.engine) as session:  # pyright: ignore[reportGeneralTypeIssues]
			log.info(f"\n{icons.INFO} SAMPLE GEAR (first 5):")
			for item in session.exec(select(GearItem).limit(5)):
				stats = f"STR+{item.strength}, INT+{item.intelligence}"
				log.info("  • {} [{}] ({})", item.text, item.type or "?", stats)
			log.info(f"\n{icons.INFO} SAMPLE QUESTS (first 5):")
			for quest in session.exec(select(QuestItem).limit(5)):
				log.info("  • {}", quest.text)
				if quest.is_boss_quest:
					log.info("    Boss: {} (HP: {})", quest.boss_name, quest.boss_hp)
			log.info(f"\n{icons.INFO} SAMPLE SPELLS (first 5):")
			for spell in session.exec(select(SpellItem).limit(5)):
				log.info("  • {} [{}]", spell.text, spell.klass or "?")
				log.info("    Level: {} | Mana: {}", spell.level, spell.mana)

	def validate_data_integrity(self) -> list[str]:
		"""Perform detailed data integrity checks for all content types.

		:return: A list of all identified issue strings.
		"""
		log.info("Performing detailed data integrity check...")
		all_issues = super().validate_data_integrity()
		with Session(self.engine) as session:  # pyright: ignore[reportGeneralTypeIssues]
			all_issues.extend(self._validate_gear_items(session))
			all_issues.extend(self._validate_quest_items(session))
			all_issues.extend(self._validate_spell_items(session))
		if all_issues:
			log.warning("Data integrity check found {} total issues.", len(all_issues))
		else:
			log.info(f"{icons.CHECK} Detailed data integrity check passed with no issues.")
		return all_issues

	def _validate_gear_items(self, session: Session) -> list[str]:
		"""Validate integrity of GearItem items.

		:param session: The active database session.
		:return: A list of issues found for GearItem items.
		"""
		issues = []
		for item in session.exec(select(GearItem)):
			if not item.text or not item.text.strip():
				issues.append(f"[Gear] Item '{item.key}' has empty text.")
			if item.value < 0:
				issues.append(f"[Gear] Item '{item.key}' has negative value: {item.value}.")
		return issues

	def _validate_quest_items(self, session: Session) -> list[str]:
		"""Validate integrity of QuestItem items.

		:param session: The active database session.
		:return: A list of issues found for QuestItem items.
		"""
		issues = []
		for quest in session.exec(select(QuestItem)):
			if not quest.text or not quest.text.strip():
				issues.append(f"[Quest] Item '{quest.key}' has empty text.")
			if quest.is_boss_quest and (quest.boss_hp is None or quest.boss_hp <= 0):
				issues.append(f"[Quest] Boss quest '{quest.key}' has invalid HP: {quest.boss_hp}.")
		return issues

	def _validate_spell_items(self, session: Session) -> list[str]:
		"""Validate integrity of SpellItem items.

		:param session: The active database session.
		:return: A list of issues found for SpellItem items.
		"""
		issues = []
		for spell in session.exec(select(SpellItem)):
			if not spell.text or not spell.text.strip():
				issues.append(f"[Spell] Item '{spell.key}' has empty text.")
			if spell.mana < 0:
				issues.append(f"[Spell] Item '{spell.key}' has negative mana: {spell.mana}.")
		return issues
