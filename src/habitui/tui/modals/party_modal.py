from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

from textual import on
from textual.screen import ModalScreen
from textual.widgets import Label, Button, OptionList
from textual.containers import Vertical, Container, Horizontal
from textual.widgets.option_list import Option

from habitui.ui import icons
from habitui.tui.generic import FieldType, FormField, GenericEditModal


if TYPE_CHECKING:
    from textual.app import ComposeResult


class SpellSelectionScreen(ModalScreen):
    """Modal screen for selecting spells to cast."""

    def __init__(self, available_spells: list, user_mp: int):
        """Initialize with available spells and user MP."""
        super().__init__()
        self.available_spells = available_spells
        self.user_mp = user_mp
        self.selected_spell = None

    def compose(self) -> ComposeResult:
        with Container(classes="input-dialog"):
            selection_screen = Vertical()
            selection_screen.border_title = f"{icons.WAND} Cast Spell"
            with selection_screen:
                yield Label("Select a spell to cast:", classes="input-label")

                spell_options = []
                for spell in self.available_spells:
                    affordable = self.user_mp >= spell.mana
                    status = icons.CHECK if affordable else icons.ERROR
                    spell_name = icons.WAND + " " + spell.text
                    spell_cost = icons.MANA + str(spell.mana)
                    spell_target = icons.TARGET + " " + spell.target
                    spell_info = spell.notes

                    grid = Table.grid(expand=True, padding=1)
                    grid.add_column()
                    grid.add_column()
                    grid.add_column()
                    grid.add_row(
                        f"[green]{status}[/]",
                        f"[blue]{spell_cost}[/] ",
                        f"[b]{spell_name}[/b]",
                    )
                    grid.add_row(
                        "",
                        f"[red]{spell_target}[/]",
                        f"[dim]{spell_info}[/dim]",
                    )

                    spell_options.append(
                        Option(grid, id=spell.key, disabled=not affordable),
                    )

                yield OptionList(*spell_options, id="spell_list", classes="input-box")

                with Horizontal(classes="modal-buttons"):
                    yield Button("Cancel", id="cancel", variant="default")
                    yield Button("Cast Spell", id="cast", variant="success")

    @on(OptionList.OptionSelected)
    def spell_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle spell selection."""
        self.selected_spell = event.option.id

    @on(Button.Pressed, "#cancel")
    def cancel_spell(self) -> None:
        """Cancel spell casting."""
        self.dismiss()

    @on(Button.Pressed, "#cast")
    def cast_spell(self) -> None:
        """Cast selected spell."""
        if not self.selected_spell:
            self.notify("Please select a spell", severity="warning")
            return

        self.dismiss(self.selected_spell)


class SpellConfirmScreen(ModalScreen):
    """Modal screen for confirming spell casting."""

    def __init__(self, spell_name: str, spell_mana: int) -> None:
        """Initialize with spell info."""
        super().__init__()
        self.spell_name = spell_name
        self.spell_mana = spell_mana

    def compose(self) -> ComposeResult:
        with Container(classes="input-dialog"):
            confirm_screen = Vertical()
            confirm_screen.border_title = f"{icons.QUESTION} Confirm Spell Cast"
            with confirm_screen:
                yield Label("Cast this spell?")
                yield Label(
                    f"{self.spell_name} ({self.spell_mana} MP)",
                    classes="spell-info",
                )

                with Horizontal(classes="modal-buttons"):
                    yield Button("Cancel", id="cancel", variant="default")
                    yield Button("Cast Spell", id="confirm", variant="success")

    @on(Button.Pressed, "#cancel")
    def cancel_spell(self) -> None:
        """Cancel spell casting."""
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def confirm_spell(self) -> None:
        """Confirm spell casting."""
        self.dismiss(True)


def create_party_message_modal() -> GenericEditModal:
    """Create a modal for composing party messages.

    :returns: An instance of `GenericEditModal` configured for party messaging.
    """
    fields = [
        FormField(
            id="message",
            label="Message:",
            field_type=FieldType.TEXTAREA,
            placeholder="Type your message to the party...",
            language="markdown",
            classes="input-box",
            required=True,
        ),
    ]

    return GenericEditModal(
        title="Send Party Message",
        fields=fields,
        icon=icons.CHAT,
        auto_focus="message",
        track_changes=False,
    )
