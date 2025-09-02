# ♥♥─── JSON Handler ─────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from typing import Any, TypeVar
from pathlib import Path

from pydantic import BaseModel, ValidationError

from habitui.custom_logger import log


T = TypeVar("T", bound=BaseModel)
JSONSerializable = dict[str, Any] | list[Any]


# ─── Resolve Path ─────────────────────────────────────────────────────────────
def _resolve_path(filepath: str | Path, folder: str | Path | None) -> Path:
    """Resolve the full file path.

    :param filepath: The base file path or filename.
    :param folder: Optional folder path.
    :return: The resolved absolute path.
    """
    if folder:
        return Path(folder).resolve() / Path(filepath).name
    return Path(filepath).resolve()


# ─── Save JSON ────────────────────────────────────────────────────────────────
def save_json(
    data: JSONSerializable,
    filepath: str | Path,
    folder: str | Path | None = None,
    indent: int = 4,
) -> bool:
    """Save a dictionary or list to a JSON file.

    :param data: The Python dictionary or list to save.
    :param filepath: The full path or filename for the output file.
    :param folder: Optional folder path.
    :param indent: JSON indentation level.
    :return: True if successful, False otherwise.
    """
    output_path = _resolve_path(filepath, folder)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    except (TypeError, OSError) as e:
        log.error("Failed to save JSON to '{}'. Error: {}", output_path, e)
        return False
    else:
        log.info("Successfully saved JSON to: '{}'", output_path)
        return True


# ─── Load JSON ────────────────────────────────────────────────────────────────
def load_json(
    filepath: str | Path,
    folder: str | Path | None = None,
) -> JSONSerializable | None:
    """Load data from a JSON file.

    :param filepath: The path or filename of the JSON file.
    :param folder: Optional folder path.
    :return: The loaded data, or None on failure.
    """
    input_path = _resolve_path(filepath, folder)
    if not input_path.is_file():
        log.warning("JSON file not found at: '{}'", input_path)
        return None
    try:
        with input_path.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.error("Failed to load or parse JSON from '{}'. Error: {}", input_path, e)
        return None


# ─── Save Model ───────────────────────────────────────────────────────────────
def save_pydantic_model(
    model: BaseModel,
    filepath: str | Path,
    folder: str | Path | None = None,
    indent: int = 2,
) -> bool:
    """Save a Pydantic model to a JSON file.

    :param model: The Pydantic model instance to save.
    :param filepath: The path or filename for the JSON file.
    :param folder: Optional folder path.
    :param indent: JSON indentation level.
    :return: True if successful, False otherwise.
    """
    output_path = _resolve_path(filepath, folder)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            model.model_dump_json(indent=indent, exclude_none=True),
            encoding="utf-8",
        )
    except (TypeError, OSError, ValidationError) as e:
        log.error("Failed to save Pydantic model to '{}'. Error: {}", output_path, e)
        return False
    else:
        log.info("Successfully saved Pydantic model to: '{}'", output_path)
        return True


# ─── Load Model ───────────────────────────────────────────────────────────────
def load_pydantic_model[T: BaseModel](model_class: type[T], filepath: str | Path, folder: str | Path | None = None) -> T | None:
    """Load a JSON file into a Pydantic model instance.

    :param model_class: The Pydantic model class (e.g., User).
    :param filepath: The path or filename of the JSON file.
    :param folder: Optional folder path.
    :return: An instance of `model_class`, or None on failure.
    """
    json_data = load_json(filepath, folder)
    # Use TypeGuard for clearer type narrowing
    if not isinstance(json_data, dict):
        if json_data is not None:
            log.warning(
                "JSON from '{}' is not a dictionary, cannot create {} model.",
                _resolve_path(filepath, folder),
                model_class.__name__,
            )
        return None
    try:
        return model_class.model_validate(json_data)
    except ValidationError as e:
        log.error("Pydantic validation failed for {}: {}", model_class.__name__, e)
        return None
