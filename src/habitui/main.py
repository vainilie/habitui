from __future__ import annotations

from habitui.tui.main_app import HabiTUI
from habitui.custom_logger import log


def main() -> None:
    """Entry point for the HabiTUI application."""
    try:
        app = HabiTUI()
        app.run()
    except Exception as e:
        log.error("An unexpected error occurred: {}", str(e))


if __name__ == "__main__":
    main()
