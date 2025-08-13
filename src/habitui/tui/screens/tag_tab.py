# ♥♥─── Tags Tab ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.binding import Binding
from textual.widgets import Tree
from textual.reactive import reactive
from textual.containers import Horizontal, VerticalScroll

from habitui.ui import icons
from habitui.core.models import TagCollection
from habitui.custom_logger import log
from habitui.tui.generic.base_tab import BaseTab
from habitui.tui.modals.tags_modal import (
    create_tag_edit_modal,
    create_tag_delete_modal,
)
from habitui.tui.generic.confirm_modal import (
    GenericConfirmModal,
    HabiticaChangesFormatter,
)
from habitui.tui.generic.dashboard_panels import (
    Panel,
    create_info_panel,
    create_dashboard_row,
)


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


class TagsTab(BaseTab):
    """Displays and manages tag hierarchy with attribute and ownership panels."""

    # ─── Configuration ─────────────────────────────────────────────────────────────
    BINDINGS: list[Binding] = [
        Binding("d", "delete_tag_workflow", "Delete"),
        Binding("a", "add_tag_workflow", "Add"),
        Binding("e", "edit_tag_workflow", "Edit"),
        Binding("c", "configure_tag_hierarchy", "Configure"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    tags_collection: reactive[TagCollection] = reactive(None, recompose=True)
    tags_count: reactive[dict] = reactive(dict, recompose=True)

    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI
        log.info("TagsTab: __init__ called")
        self.tags_collection = self.vault.ensure_tags_loaded()
        self.tags_count = self.vault.tasks.get_tag_count()  # type: ignore

    # ─── UI Composition ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Compose the layout using the new dashboard components."""
        log.info("TagsTab: compose() called")

        with VerticalScroll(classes="dashboard-main-container"):
            with Horizontal(classes="dashboard-panel-row"):
                yield self._create_attribute_tags_panel()
                yield self._create_ownership_tags_panel()

            yield self._create_tags_hierarchy_panel()

    def _create_attribute_tags_panel(self) -> Panel:
        """Create attribute tags panel using new components."""
        rows = []

        if self.tags_collection.get_str_parent():
            tag = self.tags_collection.get_str_parent()

            rows.append(
                create_dashboard_row(
                    label="STR",
                    value=tag.name,  # type: ignore
                    icon="FIRE",
                    element_id="str-tags-row",
                ),
            )

        # INT tags
        if self.tags_collection.get_int_parent():
            tag = self.tags_collection.get_int_parent()
            rows.append(
                create_dashboard_row(
                    label="INT",
                    value=tag.name,  # type: ignore
                    icon="AIR",
                    element_id="int-tags-row",
                ),
            )

        # PER tags
        if self.tags_collection.get_per_parent():
            tag = self.tags_collection.get_per_parent()
            rows.append(
                create_dashboard_row(
                    label="PER",
                    value=tag.name,  # type: ignore
                    icon="LEAF",
                    element_id="per-tags-row",
                ),
            )

        if self.tags_collection.get_con_parent():
            tag = self.tags_collection.get_con_parent()
            rows.append(
                create_dashboard_row(
                    label="CON",
                    value=tag.name,  # type: ignore
                    icon="DROP",
                    element_id="con-tags-row",
                ),
            )

        if self.tags_collection.get_no_attr_parent():
            tag = self.tags_collection.get_no_attr_parent()
            rows.append(
                create_dashboard_row(
                    label="None",
                    value=tag.name,  # type: ignore
                    icon="GHOST",
                    element_id="no-attr-tags-row",
                ),
            )

        return create_info_panel(
            *rows,
            title="Tags by Attribute",
            title_icon="WAND",
            element_id="attribute-tags-panel",
        )

    def _create_ownership_tags_panel(self) -> Panel:
        """Create ownership tags panel using new components."""
        rows = []

        # Personal tags
        if self.tags_collection.get_personal_parent():
            tag = self.tags_collection.get_personal_parent()
            rows.append(
                create_dashboard_row(
                    label="Personal",
                    value=tag.name,  # type: ignore
                    icon="USER",
                    element_id="personal-tags-row",
                ),
            )

        # Challenge tags
        if self.tags_collection.get_challenge_parent():
            tag = self.tags_collection.get_challenge_parent()
            rows.append(
                create_dashboard_row(
                    label="Challenge",
                    value=tag.name,  # type: ignore
                    icon="TROPHY",
                    element_id="challenge-tags-row",
                ),
            )

        # Legacy tags
        if self.tags_collection.get_legacy_parent():
            tag = self.tags_collection.get_legacy_parent()
            rows.append(
                create_dashboard_row(
                    label="Legacy",
                    value=tag.name,  # type: ignore
                    icon="LEGACY",
                    element_id="legacy-tags-row",
                ),
            )

        return create_info_panel(
            *rows,
            title="Tags by Ownership",
            title_icon="USER",
            element_id="ownership-tags-panel",
        )

    def _create_tags_hierarchy_panel(self) -> Panel:
        """Create tags hierarchy panel."""
        tree = self._create_tag_tree()

        return Panel(
            tree,
            title="Tag Hierarchy",
            title_icon="TREE",
            element_id="tags-hierarchy-panel",
        )

    def _create_tag_tree(self) -> Tree:
        """Create the tag tree based on current collection."""
        tree = Tree("All Tags", id="tags-tree")
        tree.root.expand()

        if not self.tags_collection:
            return tree

        # Create main nodes
        ownership_node = tree.root.add("Ownership Tags", expand=True)
        attribute_node = tree.root.add("Attribute Tags", expand=True)
        free_tags_node = tree.root.add("Free Tags", expand=True)

        # Populate based on tags_collection structure
        self._populate_tree_nodes(ownership_node, attribute_node, free_tags_node)

        return tree

    def _populate_tree_nodes(
        self,
        ownership_node,
        attribute_node,
        free_tags_node,
    ) -> None:
        """Populate tree nodes from tags collection."""
        for tag in self.tags_collection.base_tags:
            count = self.tags_count.get(tag, 0)
            name = f"{tag.name} ({count})"
            free_tags_node.add_leaf(name, data=tag)

        for tag in self.tags_collection.personal_tags:
            ownership_node.add_leaf(tag.name, data=tag)

        # Populate attribute nodes
        attribute_categories = [
            "str_tags",
            "int_tags",
            "per_tags",
            "con_tags",
            "no_attr_tags",
        ]
        attribute_labels = [
            "Strength",
            "Intelligence",
            "Perception",
            "Constitution",
            "No Attribute",
        ]

        for category, label in zip(
            attribute_categories,
            attribute_labels,
            strict=False,
        ):
            if hasattr(self.tags_collection, category):
                category_node = attribute_node.add(label, expand=False)
                for tag in getattr(self.tags_collection, category):
                    category_node.add_leaf(tag.get("name", "Unnamed"), data=tag)

    # ─── Data Handling ─────────────────────────────────────────────────────────────

    @work
    async def refresh_data(self) -> None:
        """Refresh tags data using BaseTab API access."""
        try:
            await self.vault.update_tags_only("smart", False, True)
            self.tags_collection = self.vault.ensure_tags_loaded()
            self.mutate_reactive(TagsTab.tags_collection)
            await self.vault.update_tasks_only("smart", False, True)
            self.tags_count = self.vault.tasks.get_tag_count()  # type: ignore
            self.mutate_reactive(TagsTab.tags_count)

            self.notify(
                f"{icons.CHECK} Tags data refreshed successfully!",
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

    # ─── Actions ───────────────────────────────────────────────────────────────────

    def action_add_tag_workflow(self) -> None:
        """Initiate the tag creation workflow."""
        self._add_tag_workflow()

    def action_edit_tag_workflow(self) -> None:
        """Initiate the tag editing workflow."""
        self._edit_tag_workflow()

    def action_delete_tag_workflow(self) -> None:
        """Initiate the tag deletion workflow."""
        self._delete_tag_workflow()

    def action_configure_tag_hierarchy(self) -> None:
        """Notify that hierarchy configuration is coming soon."""
        self.notify("Hierarchy configuration coming soon!", severity="information")

    @work
    async def _add_tag_workflow(self) -> None:
        """Handle tag creation workflow."""
        edit_screen = create_tag_edit_modal()
        changes = await self.app.push_screen(edit_screen, wait_for_dismiss=True)
        if changes:
            confirm_screen = GenericConfirmModal(
                question="The following tag will be created in Habitica:",
                changes=changes,
                changes_formatter=HabiticaChangesFormatter.format_changes,
                title="Confirm Tag Creation",
                icon=icons.QUESTION_CIRCLE,
            )
            confirmed = await self.app.push_screen(
                confirm_screen,
                wait_for_dismiss=True,
            )
            if confirmed:
                await self._create_tag_via_api(changes)

    @work
    async def _edit_tag_workflow(self) -> None:
        """Handle tag editing workflow."""
        tag = self._get_selected_tag()
        if not tag:
            self.notify("No tag selected to edit.", severity="warning")
            return

        edit_screen = create_tag_edit_modal(
            name=tag.get("name", ""),
            tag_id=tag.get("id", ""),
        )
        changes = await self.app.push_screen(edit_screen, wait_for_dismiss=True)
        if changes:
            confirm_screen = GenericConfirmModal(
                question="The following changes will be sent to Habitica:",
                changes=changes,
                changes_formatter=HabiticaChangesFormatter.format_changes,
                title="Confirm Tag Changes",
                icon=icons.QUESTION_CIRCLE,
            )
            confirmed = await self.app.push_screen(
                confirm_screen,
                wait_for_dismiss=True,
            )
            if confirmed:
                await self._update_tag_via_api(changes, tag.get("id", ""))

    @work
    async def _delete_tag_workflow(self) -> None:
        """Handle tag deletion workflow."""
        tag = self._get_selected_tag()
        if not tag:
            self.notify("No tag selected to delete.", severity="warning")
            return

        delete_screen = create_tag_delete_modal(tag_name=tag.get("name", ""))
        confirmed = await self.app.push_screen(delete_screen, wait_for_dismiss=True)
        if confirmed:
            await self._delete_tag_via_api(tag)

    async def _create_tag_via_api(self, changes: dict) -> None:
        """Create tag via API call."""
        try:
            log.info(f"{icons.RELOAD} Creating tag via API...")
            payload = self._build_tag_payload(changes)

            if payload:
                operations = [{"type": "create_tag", "data": payload}]
                await self.execute_operation(
                    operations,
                    "Create tag",
                    sync_after="tags",
                )

                self.refresh_data()
                self.notify(
                    f"{icons.CHECK} Tag created successfully!",
                    title="Tag Created",
                    severity="information",
                )
                log.info(f"{icons.CHECK} Tag created.")
            else:
                self.notify(
                    f"{icons.INFO} No tag data to create.",
                    title="Tag Creation",
                    severity="information",
                )
        except Exception as e:
            log.error(f"{icons.ERROR} Error creating tag: {e}")
            self.notify(
                f"{icons.ERROR} Failed to create tag: {e!s}",
                title="Error",
                severity="error",
            )

    async def _update_tag_via_api(self, changes: dict, tag_id: str) -> None:
        """Update tag via API call."""
        try:
            log.info(f"{icons.RELOAD} Updating tag via API...")
            payload = self._build_tag_payload(changes)
            payload["id"] = tag_id

            if payload:
                operations = [{"type": "update_tag", "data": payload}]
                await self.execute_operation(
                    operations,
                    "Update tag",
                    sync_after="tags",
                )

                self.refresh_data()
                self.notify(
                    f"{icons.CHECK} Tag updated successfully!",
                    title="Tag Updated",
                    severity="information",
                )
                log.info(f"{icons.CHECK} Tag updated.")
            else:
                self.notify(
                    f"{icons.INFO} No changes to save.",
                    title="Tag Update",
                    severity="information",
                )
        except Exception as e:
            log.error(f"{icons.ERROR} Error updating tag: {e}")
            self.notify(
                f"{icons.ERROR} Failed to update tag: {e!s}",
                title="Error",
                severity="error",
            )

    async def _delete_tag_via_api(self, tag: dict) -> None:
        """Delete tag via API call."""
        try:
            log.info(f"{icons.RELOAD} Deleting tag via API...")
            tag_id = tag.get("id", "")
            tag_name = tag.get("name", "Unknown")

            if tag_id:
                operations = [{"type": "delete_tag", "data": {"id": tag_id}}]
                await self.execute_operation(
                    operations,
                    f"Delete tag '{tag_name}'",
                    sync_after="tags",
                )

                self.refresh_data()
                self.notify(
                    f"{icons.CHECK} Tag '{tag_name}' deleted successfully!",
                    title="Tag Deleted",
                    severity="information",
                )
                log.info(f"{icons.CHECK} Tag deleted.")
        except Exception as e:
            log.error(f"{icons.ERROR} Error deleting tag: {e}")
            self.notify(
                f"{icons.ERROR} Failed to delete tag: {e!s}",
                title="Error",
                severity="error",
            )

    def _build_tag_payload(self, changes: dict) -> dict:
        """Build the API payload from changes."""
        payload = {}
        if "name" in changes:
            payload["name"] = changes["name"]
        return payload

    # ─── Event Handlers ────────────────────────────────────────────────────────────

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tag selection from tree."""
        if event.node.data:
            tag_name = (
                event.node.data.get("name", "Unknown")
                if isinstance(event.node.data, dict)
                else str(event.node.data)
            )
            log.info(f"Selected tag: {tag_name}")

    def _get_selected_tag(self) -> dict | None:
        try:
            tree = self.query_one("#tags-tree", Tree)
            cursor_node = tree.cursor_node
            if cursor_node and cursor_node.data and isinstance(cursor_node.data, dict):
                return cursor_node.data
        except Exception:
            pass
        return None
