# ♥♥─── App Config ───────────────────────────────────────────────────────────────
from __future__ import annotations

from pydantic import ValidationError

from habitui.ui.custom_logger import log

from .app_config_model import ApplicationSettings

# ─── Factory Function And Singleton Instance ──────────────────────────────────
_cached_settings: ApplicationSettings | None = None


# ─── Get Settings ─────────────────────────────────────────────────────────────
def get_application_settings() -> ApplicationSettings:
    """Factory function to create, load, and initialize the ApplicationSettings instance.

    :returns: The initialized :class:`ApplicationSettings` instance.
    :raises SystemExit: If configuration loading or validation fails, the application exits with a critical error.
    """
    global _cached_settings  # noqa: PLW0603

    if _cached_settings is not None:
        return _cached_settings

    log.debug("Initializing application configuration...")

    try:
        app_settings_instance = ApplicationSettings()
    except ValidationError as e:
        log.critical("CRITICAL: Application configuration validation failed.\n{}", e, exc_info=False)
        error_details = "\n".join([
            f"  - {err['loc']}: {err['msg']} (input was: {err.get('input', 'N/A')})" for err in e.errors()
        ])
        log.error("Validation error details:\n{}", error_details)
        error = "FATAL: Application configuration error. Please check your config files."
        raise SystemExit(error) from e
    except Exception as e:
        log.critical("CRITICAL: An unexpected error occurred during config initialization: {}", e, exc_info=True)
        error = "FATAL: Unexpected application configuration error."
        raise SystemExit(error) from e

    log.success("Application configuration loaded successfully.")
    log.debug("Config Directory: {}", app_settings_instance.paths.config_dir)
    log.debug("Database File Path: {}", app_settings_instance.storage.get_database_file_path())

    user_id_hint = "Not set"
    if app_settings_instance.habitica and app_settings_instance.habitica.user_id:
        user_id_hint = f"{str(app_settings_instance.habitica.user_id)[:8]}..."

    log.debug("Habitica User ID (Hint): {}", user_id_hint)
    _cached_settings = app_settings_instance

    return _cached_settings


# ─── Singleton Instance ───────────────────────────────────────────────────────
def get_settings() -> ApplicationSettings:
    """Convenient alias for getting application settings.

    :returns: The initialized :class:`ApplicationSettings` instance.
    """
    return get_application_settings()


app_config: ApplicationSettings = get_application_settings()
