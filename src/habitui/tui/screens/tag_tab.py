# ♥♥─── Tags Tab ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.binding import Binding
from textual.widgets import Tree
from textual.reactive import reactive
from textual.containers import Horizontal, VerticalScroll

from habitui.ui import icons, parse_emoji
from habitui.core.models import TagComplex, TagCollection
from habitui.tui.generic import (
    Panel,
    BaseTab,
    GenericConfirmModal,
    HabiticaChangesFormatter,
    create_info_panel,
    create_dashboard_row,
)
from habitui.custom_logger import log
from habitui.tui.modals.tags_modal import (
    create_tag_edit_modal,
    create_tag_create_modal,
    create_tag_delete_modal,
    create_batch_tag_delete_modal,
)


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.core.models import TagComplex
    from habitui.tui.main_app import HabiTUI


class TagsTab(BaseTab):
    """Displays and manages tag hierarchy with attribute and ownership panels."""

    # ─── Configuration ─────────────────────────────────────────────────────────────
    BINDINGS: list[Binding] = [
        Binding("a", "add_tag_workflow", "Add"),
        Binding("c", "configure_tag_hierarchy", "Configure"),
        Binding("d", "delete_tag_workflow", "Delete"),
        Binding("e", "edit_tag_workflow", "Edit"),
        Binding("m", "toggle_multiselect", "Multiselection"),
        Binding("n", "sort_name", "Name Sort"),
        Binding("o", "sort_original", "Default Sort"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("s", "toggle_sort", "Toggle Sort"),
        Binding("t", "tag_tasks_workflow", "Tag Tasks"),
        Binding("u", "sort_use", "Use Sort"),
        Binding("escape", "clear_selection", "Clear Selection"),
    ]

    tags_collection: reactive[TagCollection | None] = reactive(None, recompose=True)
    tags_count: reactive[dict] = reactive(dict, recompose=True)
    multiselect: reactive[bool] = reactive(False, recompose=True)
    tags_selected: reactive[list] = reactive(list)
    current_sort_index: reactive[int] = reactive(2, recompose=True)

    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI
        log.info("TagsTab: __init__ called")
        self.tags_collection = self.vault.ensure_tags_loaded()
        self.tags_count = self.vault.tasks.get_tag_count()  # type: ignore
        self.sort_modes = ["use", "name", ""]

    # ─── UI Composition ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Compose the layout using the new dashboard components."""
        log.info("TagsTab: compose() called")
        with VerticalScroll(classes="dashboard-main-container"):
            with Horizontal(classes="dashboard-panel-row"):
                if self._create_attribute_tags_panel() is not None:
                    yield self._create_attribute_tags_panel()
                if self._create_ownership_tags_panel() is not None:
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
                    value=parse_emoji(tag.name),  # type: ignore
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
                    value=parse_emoji(tag.name),  # type: ignore
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
                    value=parse_emoji(tag.name),  # type: ignore
                    icon="LEAF",
                    element_id="per-tags-row",
                ),
            )

        if self.tags_collection.get_con_parent():
            tag = self.tags_collection.get_con_parent()
            rows.append(
                create_dashboard_row(
                    label="CON",
                    value=parse_emoji(tag.name),  # type: ignore
                    icon="DROP",
                    element_id="con-tags-row",
                ),
            )

        if self.tags_collection.get_no_attr_parent():
            tag = self.tags_collection.get_no_attr_parent()
            rows.append(
                create_dashboard_row(
                    label="None",
                    value=parse_emoji(tag.name),  # type: ignore
                    icon="GHOST",
                    element_id="no-attr-tags-row",
                ),
            )
        if len(rows) > 0:
            return create_info_panel(
                *rows,
                title="Tags by Attribute",
                title_icon="WAND",
                element_id="attribute-tags-panel",
            )
        return None

    def _create_ownership_tags_panel(self) -> Panel:
        """Create ownership tags panel using new components."""
        rows = []

        # Personal tags
        if self.tags_collection.get_personal_parent():
            tag = self.tags_collection.get_personal_parent()
            rows.append(
                create_dashboard_row(
                    label="Personal",
                    value=parse_emoji(tag.name),  # type: ignore
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
                    value=parse_emoji(tag.name),  # type: ignore
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
                    value=parse_emoji(tag.name),  # type: ignore
                    icon="LEGACY",
                    element_id="legacy-tags-row",
                ),
            )
        if len(rows) > 0:
            return create_info_panel(
                *rows,
                title="Tags by Ownership",
                title_icon="USER",
                element_id="ownership-tags-panel",
            )
        return None

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

        def sort_by(
            order: str,
            tag_list: list[TagComplex],
        ) -> list[TagComplex]:
            if order == "use":
                return sorted(
                    tag_list,
                    key=lambda t: self.tags_count.get(t.id, 0),
                    reverse=True,
                )
            if order == "name":
                return sorted(tag_list, key=lambda t: t.name, reverse=False)
            return tag_list

        order = self.sort_modes[self.current_sort_index]

        def sort_tags(tags) -> list[TagComplex]:
            return sort_by(order, tags)

        # ── Base & Personal Tags ─────────────────────────────────────────────
        base_tags = sort_tags(self.tags_collection.base_tags)
        personal_tags = sort_tags(self.tags_collection.personal_tags)

        for tag in base_tags:
            count = self.tags_count.get(tag.id, 0)  # ← corregí: get por id
            name = f"({count}) {parse_emoji(tag.name)}"
            free_tags_node.add_leaf(name, data=tag)

        for tag in personal_tags:
            count = self.tags_count.get(tag.id, 0)  # ← corregí: get por id
            name = f"({count}) {parse_emoji(tag.name)}"
            ownership_node.add_leaf(name, data=tag)

        # ── Attribute Categories ─────────────────────────────────────────────
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
                tags_list = sort_tags(getattr(self.tags_collection, category))
                for tag in tags_list:
                    count = self.tags_count.get(tag.id, 0)  # ← corregí: get por id
                    name = f"({count}) {parse_emoji(tag.name)}"
                    category_node.add_leaf(name, data=tag)

    # ─── Data Handling ─────────────────────────────────────────────────────────────

    @work
    async def refresh_data(self) -> None:
        """Refresh tags data using BaseTab API access."""
        try:
            await self.vault.update_tags_only("smart", False, True)
            self.tags_collection = self.vault.tags
            await self.vault.update_tasks_only("smart", False, True)
            self.tags_count = self.vault.tasks.get_tag_count()  # type: ignore

            self.mutate_reactive(TagsTab.tags_count)
            self.mutate_reactive(TagsTab.tags_collection)

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

    def action_toggle_multiselect(self) -> None:
        if self.multiselect:
            self.multiselect = False
            self.notify("Multiselect disabled")

        else:
            self.multiselect = True
            self.notify("Multiselect enabled")

    def action_add_tag_workflow(self) -> None:
        """Initiate the tag creation workflow."""
        self._add_tag_workflow()

    def action_tag_tasks_workflow(self) -> None:
        """Initiate the tag creation workflow."""
        self._tag_tasks_workflow()

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
        edit_screen = create_tag_create_modal()
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
        tree = self.query_one("#tags-tree", Tree)
        current_node = tree.cursor_node
        if current_node and current_node.data and self.multiselect is False:
            edit_screen = create_tag_edit_modal(tag=current_node.data)

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
                    await self._update_tag_via_api(
                        changes,
                        current_node.data.id,
                    )

    @work
    async def _delete_tag_workflow(self) -> None:
        """Handle tag deletion workflow."""
        tree = self.query_one("#tags-tree", Tree)
        current_node = tree.cursor_node
        if current_node and current_node.data:
            if self.multiselect is False:
                delete_screen = create_tag_delete_modal(tag=current_node.data)
                confirmed = await self.app.push_screen(
                    delete_screen,
                    wait_for_dismiss=True,
                )
                if confirmed:
                    await self._delete_tag_via_api(current_node.data)
            elif len(self.tags_selected) > 0:
                delete_screen = create_batch_tag_delete_modal(
                    tag_list=self.tags_selected,
                    tag_uses=self.tags_count,
                )
                confirmed = await self.app.push_screen(
                    delete_screen,
                    wait_for_dismiss=True,
                )
                if confirmed:
                    for tag in self.tags_selected:
                        await self._delete_tag_via_api(tag)
                self.tags_selected.clear()

    @work
    async def _tag_tasks_workflow(self) -> None:
        challenge_tag = self.tags_collection.get_challenge_parent()
        personal_tag = self.tags_collection.get_personal_parent()

        add_ch_tag = []
        add_pe_tag = []
        del_ch_tag = []
        del_pe_tag = []

        for task in self.vault.tasks.get_challenge_tasks():
            if task.challenge:
                if challenge_tag.id not in task.tags:
                    add_ch_tag.append(task.id)
                if personal_tag.id in task.tags:
                    del_pe_tag.append(task.id)
        for task in self.vault.tasks.get_owned_tasks():
            if not task.challenge:
                if challenge_tag.id in task.tags:
                    del_ch_tag.append(task.id)
                if personal_tag.id not in task.tags:
                    add_pe_tag.append(task.id)
        add_total = len(add_pe_tag) + len(add_ch_tag)
        del_total = len(del_ch_tag) + len(del_pe_tag)
        confirm = GenericConfirmModal(
            question=f"You will tag {add_total} and untag {del_total}. Continue?",
            title="Batch Tag Tasks",
            confirm_text="Accept",
            cancel_text="Cancel",
            confirm_variant="success",
            icon=icons.QUESTION,
        )
        confirmed = await self.app.push_screen(confirm, wait_for_dismiss=True)
        if confirmed:
            changes = {
                "add": {"challenge": add_ch_tag, "personal": add_pe_tag},
                "del": {"challenge": del_ch_tag, "personal": del_pe_tag},
                "ch_tag": challenge_tag.id,
                "pe_tag": personal_tag.id,
            }
            await self._tag_tasks_via_api(changes)

    async def _tag_tasks_via_api(self, changes: dict) -> None:
        try:
            log.info(f"{icons.RELOAD} Adding/deleting tags via API...")
            for task_id in changes["add"]["challenge"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=changes["ch_tag"],
                )

            for task_id in changes["add"]["personal"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=changes["pe_tag"],
                )
            for task_id in changes["del"]["challenge"]:
                self.app.habitica_api.remove_tag_from_task(
                    task_id=task_id,
                    tag_id_to_remove=changes["ch_tag"],
                )

            for task_id in changes["del"]["personal"]:
                self.app.habitica_api.remove_tag_from_task(
                    task_id=task_id,
                    tag_id_to_remove=changes["pe_tag"],
                )
        except Exception as e:
            log.error(f"{icons.ERROR} Error adding/deleting tag: {e}")
            self.notify(
                f"{icons.ERROR} Failed to add/del tag: {e!s}",
                title="Error",
                severity="error",
            )

    async def _create_tag_via_api(self, changes: dict) -> None:
        """Create tag via API call."""
        try:
            log.info(f"{icons.RELOAD} Creating tag via API...")
            payload = self._build_tag_payload(changes)

            if payload:
                self.app.habitica_api.create_new_tag(tag_name=payload["name"])
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
                self.app.habitica_api.update_existing_tag(
                    tag_id=payload["id"],
                    new_tag_name=payload["name"],
                )
                self.tags_collection.update_tag(
                    tag_id=payload["id"],
                    update_data={"name": payload["name"]},
                )
                self.mutate_reactive(TagsTab.tags_collection)

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

    async def _delete_tag_via_api(self, tag: TagComplex) -> None:
        """Delete tag via API call."""
        try:
            log.info(f"{icons.RELOAD} Deleting tag via API...")
            self.tags_collection.remove_tag(tag.id)
            self.mutate_reactive(TagsTab.tags_collection)
            await self.client.delete_existing_tag(tag_id=tag.id)
            self.notify(
                f"{icons.CHECK} Tag '{tag.name}' deleted successfully!",
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
    def action_selected(self) -> None:
        tree = self.query_one("#tags-tree", Tree)  # Obtener el tree por ID

        current_node = tree.cursor_node
        if current_node and current_node.data:
            if self.multiselect:
                current_label = str(current_node.label)
                if current_node.data in self.tags_selected:
                    current_node.set_label(
                        f"({self.tags_count.get(current_node.data.id)}) {current_node.data.name}",
                    )
                    self.tags_selected.remove(current_node.data)
                else:
                    current_node.set_label(f"[on $accent]✓ {current_label}[/]")
                    self.tags_selected.append(current_node.data)

                log.info(f"Selected tags: {self.tags_selected}")
            log.info(f"Selected tag: {current_node.data.name}")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tag selection from tree."""
        color = self.app.theme_variables.get("block-cursor-background", "primary")
        current_node = event.node
        if current_node and current_node.data:
            if self.multiselect:
                current_label = str(event.node.label)
                if current_node.data in self.tags_selected:
                    event.node.set_label(
                        f"({self.tags_count.get(current_node.data.id)}) {current_node.data.name}",
                    )
                    self.tags_selected.remove(event.node.data)
                else:
                    event.node.set_label(f"[b {color}]✓ {current_label}[/]")
                    self.tags_selected.append(event.node.data)

                log.info(f"Selected tags: {self.tags_selected}")
            log.info(f"Selected tag: {event.node.data.name}")

    def action_toggle_sort(self):
        self.current_sort_index = (self.current_sort_index + 1) % len(self.sort_modes)

    def action_sort_use(self):
        self.sort_by = self.sort_modes.index("use")

    def action_sort_name(self):
        self.current_sort_index = self.sort_modes.index("name")

    def action_sort_original(self):
        self.current_sort_index = self.sort_modes.index("")

    def action_clear_selection(self) -> None:
        """Smart clear: clear selections first, then disable multiselect."""
        if self.tags_selected:
            tree = self.query_one("#tags-tree", Tree)
            tree.refresh()
            self.tags_selected.clear()
            log.info("Selections cleared")
            self.notify("Selection cleared")

        elif self.multiselect:
            self.multiselect = False
            log.info("Multiselect disabled")
            self.notify("Multiselect disabled")

    def action_refresh_data(self):
        self.refresh_data()
