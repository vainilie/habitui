# ♥♥─── Party Tab ────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown

from textual import work
from textual.binding import Binding
from textual.widgets import Input, Label, Static, ListItem, ListView, Collapsible
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal, VerticalScroll

from box import Box

from habitui.ui import icons, parse_emoji
from habitui.utils import DateTimeHandler
from habitui.custom_logger import log
from habitui.tui.generic.base_tab import BaseTab
from habitui.tui.modals.party_modal import (
    SpellSelectionScreen,
    create_party_message_modal,
)
from habitui.core.models.message_model import PartyMessage
from habitui.tui.generic.confirm_modal import GenericConfirmModal
from habitui.tui.generic.dashboard_panels import (
    Panel,
    create_info_panel,
    create_dashboard_row,
)


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


class PartyTab(BaseTab):
    """Displays and manages the party's information, stats, and chat."""

    # ─── Configuration ─────────────────────────────────────────────────────────────
    BINDINGS: list[Binding] = [
        Binding("e", "edit_message", "Message"),
        Binding("s", "cast_spell", "Spell"),
        Binding("j", "join_quest", "Join Quest"),
        Binding("r", "refresh_data", "Refresh"),
    ]
    party_chat_info: reactive[list[PartyMessage]] = reactive(list, recompose=True)
    party_chat_user: reactive[list[PartyMessage]] = reactive(list, recompose=True)
    user_collection: reactive[Box] = reactive(Box, recompose=True)
    party_collection: reactive[Box] = reactive(Box, recompose=True)

    def __init__(self) -> None:
        """Initialize the PartyTab."""
        super().__init__()
        self.app: HabiTUI
        log.info("PartyTab: __init__ called")
        self.party_collection = Box(self.vault.party.get_display_data())
        self.user_collection = Box(self.vault.user.get_display_data())

        self.party_chat_info = self.vault.party.get_system_messages(
            from_quest_start=True,
        )
        self.party_chat_user = self.vault.party.get_user_messages()

    # ─── UI Composition ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Compose the layout using the new dashboard components."""
        log.info("PartyTab: compose() called")
        with VerticalScroll(classes="dashboard-main-container"):
            with Horizontal(classes="dashboard-panel-row"):
                yield self._create_party_overview_panel()
                yield self._create_spells_panel()

            yield from self._create_chat_sections()
            yield self._create_description_section()

    def _create_party_overview_panel(self) -> Panel:
        """Create the party overview panel using new components."""
        rows = [
            create_dashboard_row(
                value=f"Your party is {self.party_collection.display_name}",
                icon="NORTH_STAR",
                element_id="party-overview-message",
            ),
            create_dashboard_row(
                value=f"{self.party_collection.leader_username} is leading {self.party_collection.member_count} members",
                icon="SOCIAL",
                element_id="party-leader-info",
            ),
        ]
        if self.party_collection.has_quest is True:
            quest_data = self.vault.user.get_current_quest_data(
                self.vault.game_content,
            )
            if quest_data:
                rsvp = "RSVP" if self.user_collection.get("rsvp", False) is True else ""
                quest_name = f"{rsvp} {quest_data.text}"

                rows.append(
                    create_dashboard_row(
                        label="Quest",
                        value=quest_name,
                        element_id="quest-name-row",
                    ),
                )

                if quest_data.boss_name:
                    progress_value = round(self.party_collection.quest_hp)
                    progress_total = quest_data.boss_hp if quest_data.boss_hp > 0 else 100
                    rows.append(
                        create_dashboard_row(
                            label="Boss HP",
                            value=progress_value,
                            progress_total=progress_total,
                            icon="BEAT",
                            element_id="quest-hp-row",
                        ),
                    )

                elif quest_data.has_collect:
                    total_needed = sum(item.get("count", 0) for item in quest_data.collect_items)
                    total_collected = sum(self.party_collection.quest_collect.values())
                    rows.append(
                        create_dashboard_row(
                            label="Items",
                            value=total_collected,
                            progress_total=total_needed,
                            icon="BEAT",
                            element_id="quest-collect-row",
                        ),
                    )

                status_icon = icons.QUEST if (self.party_collection.quest_active) else icons.TIMELAPSE
                rows.extend(
                    [
                        create_dashboard_row(
                            label="Joined",
                            value=str(self.party_collection.quest_members),
                            icon="SOCIAL",
                            element_id="quest-participants-row",
                        ),
                        create_dashboard_row(
                            label="Status",
                            value=status_icon,
                            icon="CLOCK",
                            element_id="quest-status-row",
                        ),
                        create_dashboard_row(
                            label="Up",
                            value=str(self.party_collection.quest_up),
                            icon="UP",
                            element_id="quest-up-votes-row",
                        ),
                        create_dashboard_row(
                            label="Down",
                            value=str(self.party_collection.quest_down),
                            icon="DOWN",
                            element_id="quest-down-votes-row",
                        ),
                    ],
                )

        return create_info_panel(
            *rows,
            title="Overview",
            title_icon="CAT",
            element_id="party-overview-panel",
        )

    def _create_spells_panel(self) -> Panel:
        """Create the spells panel using new components."""
        spell_info = self._get_spell_info()

        if not spell_info or (not spell_info.get("affordable") and not spell_info.get("non_affordable")):
            return create_info_panel(
                create_dashboard_row(
                    value="No spells available for your class",
                    icon="INFO",
                    element_id="no-spells-message",
                ),
                title="Available Spells",
                title_icon="WAND",
                element_id="available-spells-panel",
            )

        affordable = spell_info.get("affordable", [])
        non_affordable = spell_info.get("non_affordable", [])
        total = len(affordable) + len(non_affordable)

        info_row = create_dashboard_row(
            value=f"{len(affordable)}/{total} spells available",
            icon="WAND",
            element_id="spells-count-info",
        )

        spell_container = Panel(
            ListView(
                *self._create_spell_items(affordable, non_affordable),
                id="spells-display-area",
            ),
            css_classes="dashboard-panel",
            element_id="spell-list-container",
        )

        return Panel(
            info_row,
            spell_container,
            title="Available Spells",
            title_icon="WAND",
            element_id="available-spells-panel",
        )

    def _create_spell_items(
        self,
        affordable: list,
        non_affordable: list,
    ) -> list[ListItem]:
        """Create spell list items."""
        spell_items = []
        all_spells = sorted(affordable, key=lambda s: s.mana) + sorted(
            non_affordable,
            key=lambda s: s.mana,
        )

        for i in range(1, 5):
            if i <= len(all_spells):
                spell = all_spells[i - 1]
                is_affordable = spell in affordable
                css_class = "affordable-spell" if is_affordable else "unaffordable-spell"

                spell_slot = Panel(
                    Label(spell.notes, classes="value", id=f"spell-description-{i}"),
                    css_classes=f"spell-slot {css_class}",
                    element_id=f"spell-slot-{i}",
                    title=f"{icons.WAND} {spell.text}",
                    title_icon="WAND",
                )
                spell_slot.border_subtitle = f"{icons.MANA} {spell.mana} {icons.TARGET} {spell.target}"

                spell_items.append(ListItem(spell_slot))
            else:
                # Empty slot
                empty_slot = Panel(
                    Label("", classes="value", id=f"spell-description-{i}"),
                    css_classes="spell-slot",
                    element_id=f"spell-slot-{i}",
                )
                spell_items.append(ListItem(empty_slot))

        return spell_items

    def _create_chat_sections(self) -> ComposeResult:
        """Create chat sections."""
        with Collapsible(title="Chat", classes="text-box-collapsible"):
            yield Input(
                placeholder="Type your message...",
                id="chat-message-input",
                classes="input-line",
            )

            party_container = ListView(
                classes="chat-section",
                id="party-user-chat-container",
            )

            user_messages = self.party_chat_user
            party_container.border_title = f"{icons.CHAT} Party Chat ({len(user_messages)})"

            with party_container:
                for message in user_messages:
                    class_icon = _get_class_icon(
                        message.user_class.lower() if message.user_class else "",
                    )

                    msg_item = ListItem(
                        Label(Markdown(parse_emoji(message.text))),
                        classes="user-message",
                    )
                    msg_item.border_title = f"{class_icon} {parse_emoji(message.user)}"
                    msg_item.border_subtitle = f"{icons.HEART_O} {len(message.likes)} {icons.CLOCK_O} {DateTimeHandler(timestamp=message.timestamp).format_time_difference()}"

                    yield msg_item

        with Collapsible(title="System", classes="text-box-collapsible"):
            system_container = Vertical(
                classes="chat-section",
                id="system-chat-container",
            )

            system_messages = self.party_chat_info
            system_container.border_title = f"{icons.ROBOT} System Messages ({len(system_messages)})"

            with system_container:
                for message in system_messages:
                    message_clean = "* " + message.unformatted_text

                    msg_static = Static(
                        Markdown(message_clean),
                        classes="system-message",
                    )
                    msg_static.border_subtitle = f"{icons.CLOCK_O} {DateTimeHandler(timestamp=message.timestamp).format_time_difference()}"

                    yield msg_static

    def _create_description_section(self) -> Collapsible:
        """Create the party description section."""
        party_info = self.party_collection
        party_name = party_info.display_name if party_info else "Loading..."

        biography_section = Collapsible(
            Panel(
                Static(
                    Markdown(parse_emoji(party_info.summary) if party_info else ""),
                    id="party-summary-content",
                    classes="markdown-box",
                ),
                title="Summary",
                title_icon="FEATHER",
                element_id="party-summary-panel",
            ),
            Panel(
                Static(
                    Markdown(parse_emoji(party_info.description) if party_info else ""),
                    id="party-description-content",
                    classes="markdown-box",
                ),
                title="Description",
                title_icon="CARD",
                element_id="party-description-panel",
            ),
            classes="text-box-collapsible",
            id="party-biography-collapsible",
            title="Description",
        )
        biography_section.border_title = f"{icons.FEATHER} Description"
        biography_section.border_subtitle = f"{icons.AT} {party_name}"

        return biography_section

    # ─── Event Handling ────────────────────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission events."""
        if event.input.id == "chat-message-input":
            await self._send_chat_message()

    # ─── Actions ───────────────────────────────────────────────────────────────────

    def action_refresh_data(self) -> None:
        """Refresh party data."""
        self.refresh_data()

    def action_edit_message(self) -> None:
        """Open dialog for sending a party message."""
        self._send_party_message_workflow()

    def action_cast_spell(self) -> None:
        """Open dialog for casting spells."""
        self._cast_party_spell_workflow()

    async def action_join_quest(self) -> None:
        """Join the current party quest."""
        if self.user_collection.rsvp is True:
            await self.app.habitica_api.accept_party_quest_invite()
            self.notify(
                f"{icons.CHECK} Joined Quest!",
                title="Party Quest",
                severity="information",
            )
        else:
            self.notify(
                f"{icons.CHECK} Already joined to a quest!",
                title="Party Quest",
                severity="information",
            )

    # ─── Data & Workflows ──────────────────────────────────────────────────────────

    @work
    async def refresh_data(self) -> None:
        """Refresh party and user data from the API."""
        try:
            await self.vault.update_party_only("smart", False, True)
            await self.vault.update_user_only("smart", False, True, False)
            party = self.vault.ensure_party_loaded()

            self.party_collection = Box(party.get_display_data())
            self.user_collection = self.vault.user.get_display_data()
            self.party_chat_info = party.get_system_messages(from_quest_start=True)
            self.party_chat_user = party.get_user_messages()
            self.mutate_reactive(PartyTab.party_collection)
            self.mutate_reactive(PartyTab.user_collection)
            self.mutate_reactive(PartyTab.party_chat_info)
            self.mutate_reactive(PartyTab.party_chat_user)

            self.notify(
                f"{icons.CHECK} Party data refreshed successfully!",
                title="Data Refreshed",
                severity="information",
            )
        except Exception as e:
            log.error(f"{icons.ERROR} Error refreshing data: {e}")
            self.notify(
                f"{icons.ERROR} Failed to refresh data: {e}",
                title="Error",
                severity="error",
            )

    @work
    async def _send_party_message_workflow(self) -> None:
        """Handle the complete workflow for sending a party message."""
        message_modal = create_party_message_modal()
        result = await self.app.push_screen(message_modal, wait_for_dismiss=True)

        if not (result and "message" in result):
            return

        message = result["message"].strip()

        if message:
            confirm_modal = GenericConfirmModal(
                question=f"Send this message to your party?\n\n{message[:100]}{'...' if len(message) > 100 else ''}",
                title="Confirm Message",
                icon=icons.CHAT,
            )
            confirmed = await self.app.push_screen(
                confirm_modal,
                wait_for_dismiss=True,
            )

            if confirmed:
                await self._send_message_via_api(message)

    async def _send_message_via_api(self, message: str) -> None:
        """Send a message to the group chat via the API."""
        try:
            log.info(f"{icons.CHAT} Sending party message: {message}")
            await self.app.habitica_api.post_message_to_group_chat(
                message_content=message,
            )
            self.refresh_data()
            self.notify(
                f"{icons.CHECK} Message sent!",
                title="Party Chat",
            )
            log.info(f"{icons.CHECK} Party message sent")
        except Exception as e:
            log.error(f"{icons.ERROR} Error sending message: {e}")
            self.notify(
                f"{icons.ERROR} Failed to send message",
                title="Error",
                severity="error",
            )

    async def _send_chat_message(self) -> None:
        """Send a message from the chat input field."""
        message_input = self.query_one("#chat-message-input", Input)
        message = message_input.value.strip()

        if not message:
            self.notify(
                f"{icons.WARNING} Message cannot be empty",
                title="Message",
                severity="warning",
            )

            return

        message_input.value = ""
        await self._send_message_via_api(message)

    @work
    async def _cast_party_spell_workflow(self) -> None:
        """Handle the complete workflow for casting a class spell."""
        try:
            spell_info = self._get_spell_info()

            if not spell_info:
                self.notify(
                    f"{icons.INFO} No spell information available",
                    title="Spells",
                )

                return

            affordable_spells = spell_info.get("affordable", [])
            current_mp = spell_info.get("current_mana", 0)

            if not affordable_spells:
                if not spell_info.get("affordable") and not spell_info.get(
                    "non_affordable",
                ):
                    self.notify(
                        f"{icons.INFO} No spells available for your class",
                        title="Spells",
                        severity="information",
                    )
                else:
                    cheapest = min(
                        spell_info.get("non_affordable", []),
                        key=lambda s: s.mana,
                    )
                    mp_needed = cheapest.mana - current_mp
                    self.notify(
                        f"{icons.WARNING} Not enough MP. Need {mp_needed} more MP for cheapest spell ({cheapest.text}).",
                        title="Insufficient MP",
                        severity="warning",
                    )
                return

            spell_key = await self._select_spell(affordable_spells, current_mp)
            if spell_key:
                await self._confirm_and_cast_spell(spell_key, affordable_spells)

        except Exception as e:
            log.error(f"Error in spell casting workflow: {e}")
            self.notify(
                f"{icons.ERROR} Error accessing spells",
                title="Error",
                severity="error",
            )

    async def _confirm_and_cast_spell(self, selected_spell) -> None:
        """Confirm and cast the selected spell."""
        if not selected_spell:
            log.error("No spell selected.")
            self.notify(
                f"{icons.ERROR} No spell selected.",
                title="Error",
                severity="error",
            )

            return

        confirm_modal = GenericConfirmModal(
            question=f"Cast '{selected_spell.text}' for {selected_spell.mana} MP?\n\n{selected_spell.notes}",
            title="Confirm Spell Cast",
            icon=icons.WAND,
        )
        confirmed = await self.app.push_screen(confirm_modal, wait_for_dismiss=True)

        if confirmed:
            await self._cast_spell_via_api(selected_spell.key, selected_spell.text)

    async def _select_spell(self, affordable_spells: list, user_mp: int) -> str | None:
        """Handle spell selection screen."""
        spell_screen = SpellSelectionScreen(affordable_spells, user_mp)
        return await self.app.push_screen(spell_screen, wait_for_dismiss=True)

    async def _cast_spell_via_api(self, spell_key: str, spell_name: str) -> None:
        """Cast a spell on the party via the API."""
        try:
            log.info(f"{icons.WAND} Casting spell: {spell_key} ({spell_name})")
            await self.client.cast_skill_on_target(spell_key)

            await self.vault.update_user_only("smart", False, True, False)
            self.refresh_data()

            self.notify(
                f"{icons.WAND} '{spell_name}' cast successfully!",
                title="Spell Cast",
            )
            log.info(f"{icons.CHECK} Spell cast successfully: {spell_key}")

        except Exception as e:
            log.error(f"{icons.ERROR} Error casting spell {spell_key}: {e}")
            self.notify(
                f"{icons.ERROR} Failed to cast '{spell_name}': {e!s}",
                title="Spell Failed",
                severity="error",
            )

    # ─── Helpers ───────────────────────────────────────────────────────────────────

    def _get_quest_data(self):
        """Get quest data from the content vault."""
        return self.vault.user.get_current_quest_data(
            content_vault=self.vault.game_content,
        )

    def _get_spell_info(self):
        """Get available spell information for the user."""
        return self.vault.user.available_spells(content_vault=self.vault.game_content)
