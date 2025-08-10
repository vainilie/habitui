# ♥♥─── Themed Icon Provider ───────────────────────────────────────────────────
from __future__ import annotations

from typing import Literal, ClassVar
from functools import lru_cache

from .icon_definitions import IconName


# ─── Icon Retriever ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=256)
def get_icon(icon_name: str, shape: str | None = None, outline: bool = False, alt: bool = False) -> str:
	"""Find the best-matching icon variant based on theme settings."""
	candidates = []
	suffix = "_O" if outline else ""

	if shape:
		base = f"{icon_name}_{shape.upper()}{suffix}"
		if alt:
			candidates.append(f"{base}_ALT")
		candidates.append(base)

	if alt:
		candidates.append(f"{icon_name}_ALT")

	if outline:
		candidates.append(f"{icon_name}_O")

	candidates.append(icon_name)

	for variant in candidates:
		if hasattr(IconName, variant):
			return getattr(IconName, variant).value

	return "●"


# ─── Themed Icon Class ──────────────────────────────────────────────────────────
class ThemedIcons:
	"""Provide themed icons with support for shapes, outlines, and alternates."""

	AVAILABLE_ICONS: ClassVar[set[str]] = {
		"ACCESSIBILITY",
		"AIR",
		"ANCHOR",
		"ANKH",
		"ANTIDOTE",
		"ARCHIVE",
		"ASTERISK",
		"AT",
		"BACK",
		"BACK_FAST",
		"BACK_STEP",
		"BAG",
		"BAHAI",
		"BAN",
		"BANNED",
		"BEAT",
		"BED",
		"BELL",
		"BLANK",
		"BOOK",
		"BOOKMARK",
		"BOTTLE",
		"BRAIN",
		"BRANCH",
		"BRUSH",
		"BUBBLE",
		"BUG",
		"BULB",
		"BUTTERFLY",
		"BUY",
		"CALENDAR",
		"CALENDAR_CHECK",
		"CALENDAR_ERROR",
		"CALENDAR_MINUS",
		"CALENDAR_MONTH",
		"CALENDAR_PLUS",
		"CAMERA",
		"CARD",
		"CAT",
		"CHART",
		"CHART_PASTEL",
		"CHART_UP",
		"CHAT",
		"CHECK",
		"CHECK_DOUBLE",
		"CHEVRON_DOWN",
		"CHEVRON_LEFT",
		"CHEVRON_RIGHT",
		"CHEVRON_UP",
		"CHRISTIAN",
		"CLIP",
		"CLOCK",
		"CLOTHES",
		"CLOUD",
		"CODE",
		"COFFEE",
		"COINS",
		"COLUMN",
		"COLUMNS",
		"COMPASS",
		"CONTACTS",
		"CONVERSATION",
		"CONVERSATION_READ",
		"CONVERSATION_UNREAD",
		"CONVERSATION_UNRESPONDED",
		"COPY",
		"CREATE",
		"CROW",
		"CUT",
		"D20",
		"DATABASE",
		"DELETE",
		"DESKTOP",
		"DHARMACHAKRA",
		"DIAMOND",
		"DICE",
		"DOG",
		"DOLLAR",
		"DOT",
		"DOWN",
		"DOWN_CHEVRON",
		"DOWNLOAD",
		"DRAGON",
		"DROP",
		"DUNGEON",
		"DUPLICATE",
		"EDIT",
		"EJECT",
		"ELLIPSIS_H",
		"ELLIPSIS_V",
		"ENTER",
		"ERASE",
		"ERROR",
		"EXIT",
		"EXCLAMATION",
		"EXPLOSION",
		"EXTERNAL_LINK",
		"EYE",
		"EYE_CROSS",
		"FAN",
		"FAVOURITE",
		"FEATHER",
		"FIGURE",
		"FILE",
		"FILE_TEXT",
		"FILTER",
		"FIRE",
		"FLAG",
		"FLAME",
		"FLASH",
		"FOLDER",
		"FROG",
		"FRUIT",
		"GEAR",
		"GEM",
		"GHOST",
		"GIFT",
		"GIT",
		"GLASSES",
		"GOAL",
		"GOPURAM",
		"GRADUATE",
		"GRID",
		"GROUP",
		"H",
		"HALF",
		"HAMMER",
		"HAMSA",
		"HASHTAG",
		"HEADER",
		"HEADPHONE",
		"HEART",
		"HISTORY",
		"HOME",
		"HORIZONTAL",
		"HORSE",
		"HOURGLASS",
		"ICECREAM",
		"INBOX",
		"INFINITY",
		"INFO",
		"ITALIC",
		"ITERATIONS",
		"JADE",
		"JEDI",
		"KEY",
		"KHANDA",
		"KID",
		"LANGUAGES",
		"LAPTOP",
		"LAYOUT",
		"LEAF",
		"LEAVES",
		"LEFT",
		"LEFT_CHEVRON",
		"LEFT_LONG",
		"LESSON",
		"LINES",
		"LINK",
		"LIST",
		"LIST_ORDERED",
		"LIST_UNORDERED",
		"LOCATION",
		"LOCK",
		"LOCK_OFF",
		"LOTUS",
		"MAN",
		"MAP_PIN",
		"MARKDOWN",
		"MEDICAL",
		"MEGAPHONE",
		"MERGE",
		"MILESTONE",
		"MINUS",
		"MOBILE",
		"MONEY",
		"MONSTER",
		"MOON",
		"MOUNTAIN",
		"MOVE",
		"MOVE_HORIZONTAL",
		"MOVE_TO_BOTTOM",
		"MOVE_TO_TOP",
		"MOVE_VERTICAL",
		"MSG_READ",
		"MSG_UNREAD",
		"MSG_UNREAD_COUNT",
		"MULTIMEDIA",
		"MULTISELECT",
		"MUSEUM",
		"MUSIC",
		"NEWS",
		"NEXT",
		"NEXT_FAST",
		"NEXT_STEP",
		"NORTH_STAR",
		"NOTE",
		"NUMBERS",
		"OBSIDIAN",
		"OM",
		"OTTER",
		"OWL",
		"PALETTE",
		"PAPERCLIP",
		"PATH",
		"PAUSE",
		"PAW",
		"PEN",
		"PENCIL",
		"PESO",
		"PHOENIX",
		"PICTURE",
		"PILL",
		"PIN",
		"PINE",
		"PIZZA",
		"PLAY",
		"PLUG",
		"PLUS",
		"POISON",
		"POMODORO_AWAY",
		"POMODORO_CLEAN_CODE",
		"POMODORO_DONE",
		"POMODORO_EXTERNAL_INTERRUPTION",
		"POMODORO_INTERNAL_INTERRUPTION",
		"POMODORO_NEW",
		"POMODORO_PAIR",
		"POMODORO_PAUSE_LONG",
		"POMODORO_PAUSE_SHORT",
		"POMODORO_PROGRESS",
		"POMODORO_SQUASHED",
		"POOP",
		"POWER",
		"PRAY",
		"PRESCRIPTION",
		"PROFILE",
		"PROJECT",
		"PROJECT_ROADMAP",
		"PUZZLE",
		"QUESTION",
		"READ",
		"READER",
		"RECORD",
		"RECYCLE",
		"REDO",
		"RELOAD",
		"REPEAT",
		"REPLY",
		"RESISTANCE",
		"RIGHT",
		"RIGHT_CHEVRON",
		"ROBOT",
		"ROCKET",
		"ROWS",
		"SAVE",
		"SCROLL",
		"SEARCH",
		"SEED",
		"SEND",
		"SHARE",
		"SHIELD",
		"SHOWER",
		"SHUFFLE",
		"SIGNATURE",
		"SKILL",
		"SKULL",
		"SLASH",
		"SLIDERS",
		"SMALL",
		"SNAKE",
		"SNOW",
		"SOCIAL",
		"SOFA",
		"SPARK",
		"SPARKS",
		"SPRAY",
		"SQUIRREL",
		"STACK",
		"STAR",
		"STAR_HALF",
		"STAR_HALF_STROKE",
		"STAR_OCTAGON",
		"STARRY",
		"STICKY",
		"STOP",
		"STORE",
		"STRENGTH",
		"SUN",
		"SWITCH",
		"SWITCH_OFF",
		"SWITCH_ON",
		"TABLE",
		"TABLET",
		"TAG",
		"TAGS",
		"TARGET",
		"TASK_LIST",
		"TELESCOPE",
		"TERMINAL",
		"TEXT",
		"THEMES",
		"TIMER",
		"TOOL",
		"TORII",
		"TREE",
		"TRIANGLE_DOWN",
		"TRIANGLE_LEFT",
		"TRIANGLE_RIGHT",
		"TRIANGLE_UP",
		"TROPHY",
		"UNDO",
		"UNLINK",
		"UP",
		"UP_CHEVRON",
		"UP_DOWN",
		"UPLOAD",
		"USER",
		"USER_AGENT",
		"USER_NINJA",
		"USER_NURSE",
		"USER_SHIELD",
		"VANILLA",
		"VERTICAL_LINE",
		"VIDEO",
		"VIHARA",
		"WALK",
		"WALLET",
		"WAND",
		"WARNING",
		"WATCH",
		"WEB",
		"WHEELCHAIR",
		"WIN",
		"WIZARD",
		"WOMAN",
		"WORK",
		"WORKFLOW",
		"WRITE",
		"YEN",
		"YIN_YANG",
	}

	def __init__(
		self,
		shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] = "SIMPLE",
		outline: bool = False,
		alt: bool = False,
	) -> None:
		"""Initialize the icon theme."""
		self.shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] | None = shape if shape != Literal["SIMPLE"] else None
		self.outline = outline
		self.alt = alt

	def __getattr__(self, name: str) -> str:
		"""Dynamically retrieve an icon by its base name."""
		if name in self.AVAILABLE_ICONS:
			return get_icon(name, self.shape, self.outline, self.alt)

		if hasattr(IconName, name):
			return getattr(IconName, name).value

		msg = f"Icon '{name}' not found. Available: {sorted(self.AVAILABLE_ICONS)}"
		raise AttributeError(msg)

	def get_specific(self, icon_name: str) -> str:
		"""Get a specific icon variant by its full name."""
		if hasattr(IconName, icon_name):
			return getattr(IconName, icon_name).value

		msg = f"Icon variant '{icon_name}' not found"
		raise ValueError(msg)

	def with_theme(
		self,
		shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] | None = None,
		outline: bool | None = None,
		alt: bool | None = None,
	) -> ThemedIcons:
		"""Create a new ThemedIcons instance with modified theme settings."""
		new_shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] = shape if shape is not None else (self.shape or "SIMPLE")

		return ThemedIcons(
			shape=new_shape,
			outline=outline if outline is not None else self.outline,
			alt=alt if alt is not None else self.alt,
		)

	def list_variants(self, base_name: str) -> list[str]:
		"""List all available variants for a base icon name."""
		upper_base_name = base_name.upper()

		return [icon.name for icon in IconName if icon.name.startswith(upper_base_name)]

	def __dir__(self) -> list[str]:
		"""Provide a list of available icons for autocompletion."""
		methods = ["get_specific", "with_theme", "list_variants"]

		return [*sorted(self.AVAILABLE_ICONS), *methods]


# ─── Pre-configured Themes ──────────────────────────────────────────────────────
class Icons:
	"""Provide easy access to pre-configured icon themes."""

	simple = ThemedIcons(shape="SIMPLE", outline=False, alt=False)
	circle = ThemedIcons(shape="CIRCLE", outline=False, alt=False)
	circle_outline = ThemedIcons(shape="CIRCLE", outline=True, alt=False)
	square = ThemedIcons(shape="SQUARE", outline=False, alt=False)
	square_outline = ThemedIcons(shape="SQUARE", outline=True, alt=False)

	@classmethod
	def custom(
		cls,
		shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] = "SIMPLE",
		outline: bool = False,
		alt: bool = False,
	) -> ThemedIcons:
		"""Create a ThemedIcons instance with a custom theme."""
		return ThemedIcons(shape, outline, alt)
