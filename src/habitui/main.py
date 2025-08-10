from __future__ import annotations

import asyncio

from habitui.core.client import HabiticaClient
from habitui.custom_logger import log
from habitui.core.services.data_vault import DataVault


async def async_main() -> None:
	"""Main execution flow: fetches data, stores it, and demonstrates access."""
	try:
		# 1. Initialization
		client = HabiticaClient()
		vault = DataVault(client=client)

		# 2. Fetch data
		await vault.get_data(debug=True, mode="smart", force=False)

		# 3. Show summary
		summary = vault.get_data_summary()
		log.info("Data loaded successfully: {}", summary)

	except Exception as e:
		log.error("Error in main: {}", str(e))
		raise


def main() -> None:
	"""Entry point para pyproject.toml - función síncrona que ejecuta async_main."""
	asyncio.run(async_main())


if __name__ == "__main__":
	main()
