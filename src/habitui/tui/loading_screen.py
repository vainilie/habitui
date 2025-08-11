
		self.setup_logging_integration()

		self.setup_banner_styling()

		self.logger.info("Starting HabiTUI...")
		self.title = "HabiTUI"
		self.theme = "rose_pine"

		self.load_vault_and_main_screen()

	def setup_banner_styling(self) -> None:
		"""
		Applies styles to the ASCII art banner.
		"""
		try:
			banner = self.query_one("#ascii-banner", Static)
			banner.styles.color = "rgb(235,188,186)"  # rose gold
			banner.styles.text_align = "center"

		except Exception as e:
			self.logger.warning(f"Could not style the banner: {e}")

	def setup_logging_integration(self) -> None:
		"""
		Sets up integration with the Textual logging console.
		Ensures log messages are displayed within the TUI.
		"""
		if self._textual_sink_id is not None:
			return

		try:
			log_console = self.query_one("#log-console", TextualLogConsole)
			textual_sink = TextualSink(log_console)

			self._textual_sink_id = self.logger.add(
				sink=textual_sink,
				level="INFO",
				format="{message}",
				colorize=False,
				backtrace=False,
				diagnose=False,
			)

			self.logger.info("Logging integration configured.")

		except Exception as e:
			self.logger.error(f"Error setting up logging integration: {e}")

	# ─── Data Loading and Screen Transition ────────────────────────────────────────

	@work(exclusive=True)
	async def load_vault_and_main_screen(self) -> None:
		"""
		Loads the DataVault and transitions to the MainScreen.
		This operation runs in a background worker thread.
		"""
		try:
			self.logger.info("Starting vault load...")

			self.vault = DataVault()
			await self.vault.get_data("smart", False, False, False, True)

			self.logger.info("Vault loaded successfully.")

			self.logger.info("Transitioning to MainScreen...")
			self._loading_complete = True

			self.push_screen(MainScreen())

		except Exception as e:
			self.logger.error(f"Error during data loading: {e}")
