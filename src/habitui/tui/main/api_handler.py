# ♥♥─── Queued API Handler ──────────────────────────────────────────
# Standard Library
from __future__ import annotations

from typing import TYPE_CHECKING, Any
import asyncio
from collections import deque
from collections.abc import Coroutine

from textual.widgets import Static, ProgressBar
from textual.reactive import reactive
from textual.containers import Horizontal

from habitui.ui import icons
from habitui.core.client import HabiticaClient


if TYPE_CHECKING:
    from habitui.tui.main_app import HabiTUI


class SimpleProgressWidget(Horizontal):
    """Simple widget to display queue progress."""

    current: reactive[int] = reactive(0)
    total: reactive[int] = reactive(0)
    is_working: reactive[bool] = reactive(False, layout=True)
    status: reactive[str] = reactive("")

    def on_mount(self) -> None:
        """Set initial hidden state when the widget is first added."""
        self.add_class("hidden")

    def watch_is_working(self, is_working: bool) -> None:
        """Watch for changes in 'is_working' and toggle the 'hidden' class."""
        # Este método es la clave:
        # Si is_working es True, quita la clase .hidden
        # Si is_working es False, pone la clase .hidden
        self.set_class(not is_working, "hidden")

    def compose(self):
        """Compose the progress widget UI."""
        yield ProgressBar(total=100, show_eta=True, id="progress")
        yield Static("", id="status")

    def show_progress(self, current: int, total: int, status: str = "") -> None:
        """Update and show the progress bar and status text."""
        self.current = current
        self.total = total
        self.status = status

        progress_bar = self.query_one("#progress", ProgressBar)
        progress_bar.total = total
        progress_bar.progress = current

        status_text = self.query_one("#status", Static)
        if status:
            status_text.update(f"{status} ({current}/{total})")
        else:
            status_text.update(f"Processing... ({current}/{total})")

        # 2. Hazlo visible (esto llamará a watch_is_working)
        self.is_working = True

    def hide_progress(self) -> None:
        """Hide and reset the progress widget."""
        self.is_working = False
        progress_bar = self.query_one("#progress", ProgressBar)
        progress_bar.total = 0
        progress_bar.progress = 0
        status_text = self.query_one("#status", Static)
        status_text.update("")


class QueuedAPIHandler:
    """Accumulate API operations and execute them as a batch."""

    def __init__(self, app: HabiTUI) -> None:
        """Initialize the API handler."""
        super().__init__()
        self.app = app
        self.client: HabiticaClient = HabiticaClient()
        self.operations_queue: deque[tuple[str, Coroutine[Any, Any, Any]]] = deque()
        self.is_processing: bool = False
        self._auto_process_task: asyncio.Task | None = None
        self.progress_widget = SimpleProgressWidget()

    def _update_progress(self, current: int, total: int, status: str = "") -> None:
        """Update the visual progress indicator."""
        self.progress_widget.show_progress(current, total, status)

    def _finish_progress(self) -> None:
        """Hide the visual progress indicator."""
        self.progress_widget.hide_progress()
        self.is_processing = False

    # ─── Direct Execution ──────────────────────────────────────────────────────────
    async def call_direct(self, operation_name: str, **kwargs: Any) -> Any:
        """Execute an operation immediately, bypassing the queue."""
        try:
            if self.progress_widget and not self.is_processing:
                self.progress_widget.show_progress(0, 1, f"Executing {operation_name}")
            method = getattr(self.client, operation_name)
            result = await method(**kwargs)
            if self.progress_widget and not self.is_processing:
                self.progress_widget.show_progress(
                    1,
                    1,
                    f"{icons.CHECK} {operation_name}",
                )
                await asyncio.sleep(0.5)
                self.progress_widget.hide_progress()
            self.app.logger.info(
                f"{icons.BOLT} Direct execution: {operation_name}",
            )
            return result
        except Exception:
            if self.progress_widget and not self.is_processing:
                self.progress_widget.hide_progress()
            self.app.logger.error(
                "Direct execution error in {operation_name}: {e}",
            )
            raise

    # ─── Queue Management ──────────────────────────────────────────────────────────
    def queue_operation(self, operation_name: str, **kwargs: Any) -> None:
        """Add an operation to the queue for batch processing."""
        coroutine = getattr(self.client, operation_name)(**kwargs)
        self.operations_queue.append((operation_name, coroutine))
        self.app.logger.info(
            f"{icons.CREATE} Queued: {operation_name} (Total: {len(self.operations_queue)})",
        )
        self._schedule_auto_process()

    def _schedule_auto_process(self) -> None:
        """Schedule a delayed task to process the queue."""
        if self._auto_process_task:
            self._auto_process_task.cancel()

        async def delayed_process() -> None:
            await asyncio.sleep(0.5)
            if self.operations_queue and not self.is_processing:
                await self.process_queue()

        self._auto_process_task = asyncio.create_task(delayed_process())

    async def process_queue(self) -> list[Any]:
        """Execute all pending operations in the queue."""
        if not self.operations_queue:
            self.app.logger.info(
                f"{icons.LOADING} Queue is empty, nothing to process.",
            )
            return []
        if self.is_processing:
            self.app.logger.warning(
                f"{icons.HOURGLASS} Queue processing is already in progress.",
            )
            return []
        self.is_processing = True
        total_operations = len(self.operations_queue)
        results: list[Any] = []
        success_count = 0
        self.app.logger.info(
            f"{icons.ROCKET} Processing queue: {total_operations} operations",
        )
        self._update_progress(0, total_operations, "Initializing...")
        await asyncio.sleep(0.2)
        for i in range(total_operations):
            operation_name, coroutine = self.operations_queue.popleft()
            current_step = i + 1
            try:
                self._update_progress(
                    i,
                    total_operations,
                    f"Executing {operation_name}",
                )
                result = await coroutine
                results.append(result)
                success_count += 1
                self._update_progress(
                    current_step,
                    total_operations,
                    f"{icons.CHECK} {operation_name}",
                )
                self.app.logger.info(
                    f"{icons.CHECK} {current_step}/{total_operations}: {operation_name}",
                )
                await asyncio.sleep(0.1)
            except Exception as e:
                results.append(None)
                self.app.logger.error(
                    f"{icons.ERROR} {current_step}/{total_operations}: {operation_name} - {e}",
                )
                self._update_progress(
                    current_step,
                    total_operations,
                    f"{icons.ERROR} Error: {operation_name}",
                )
                await asyncio.sleep(0.3)
        final_message = f"{icons.CHECK} Queue processed: {success_count}/{total_operations} successful"
        self._update_progress(total_operations, total_operations, final_message)
        self.app.logger.info(f"{icons.STAR_OF_LIFE} {final_message}")
        if self.app:
            self.app.notify(final_message, title="API Queue Complete")
        await asyncio.sleep(1.5)
        self._finish_progress()
        return results

    # ─── Utility & Status Methods ────────────────────────────────────────────────
    def clear_queue(self) -> None:
        """Clear all operations from the queue without execution."""
        if self._auto_process_task:
            self._auto_process_task.cancel()
            self._auto_process_task = None
        count = len(self.operations_queue)
        self.operations_queue.clear()
        self.app.logger.info(
            f"{icons.DELETE} Queue cleared: {count} operations discarded",
        )

    def force_process_now(self) -> None:
        """Force immediate processing of the queue, bypassing the delay."""
        if self._auto_process_task:
            self._auto_process_task.cancel()
        if self.operations_queue and not self.is_processing:
            asyncio.create_task(self.process_queue())

    def queue_size(self) -> int:
        """Return the number of operations currently in the queue."""
        return len(self.operations_queue)

    def can_close_app(self) -> bool:
        """Check if it is safe to close the application."""
        return not self.is_processing

    def is_busy(self) -> bool:
        """Check if the handler is processing or has pending items."""
        return self.is_processing or bool(self.operations_queue)

    def get_status(self) -> str:
        """Get a human-readable status of the handler."""
        if self.is_processing:
            return "Processing queue..."
        if self.operations_queue:
            return f"{len(self.operations_queue)} operations in queue"
        return "Ready"

    # ─── Queued Operations (Tags) ────────────────────────────────────────────────
    def queue_tag_create(self, tag_name: str) -> None:
        """Queue the creation of a new tag."""
        self.queue_operation("create_new_tag", tag_name=tag_name)

    def queue_tag_delete(self, tag_id: str) -> None:
        """Queue the deletion of an existing tag."""
        self.queue_operation("delete_existing_tag", tag_id=tag_id)

    def queue_tag_update(self, tag_id: str, **kwargs: Any) -> None:
        """Queue an update for an existing tag."""
        self.queue_operation("update_existing_tag", tag_id=tag_id, **kwargs)

    def queue_add_tag_to_task(self, task_id: str, tag_id: str) -> None:
        """Queue adding a tag to a task."""
        self.queue_operation("add_tag_to_task", task_id=task_id, tag_id=tag_id)

    def queue_remove_tag_from_task(self, task_id: str, tag_id: str) -> None:
        """Queue removing a tag from a task."""
        self.queue_operation("remove_tag_from_task", task_id=task_id, tag_id=tag_id)

    # ─── Batch Queued Operations ─────────────────────────────────────────────────
    def queue_multiple_tag_creates(self, tag_names: list[str]) -> None:
        """Queue the creation of multiple new tags."""
        for name in tag_names:
            coroutine = self.client.create_new_tag(tag_name=name)
            self.operations_queue.append(("create_new_tag", coroutine))
            self.app.logger.info(f"{icons.CREATE} Queued: create_new_tag {name}")
        self._schedule_auto_process()

    def queue_multiple_tag_deletes(self, tag_ids: list[str]) -> None:
        """Queue the deletion of multiple existing tags."""
        for tag_id in tag_ids:
            coroutine = self.client.delete_existing_tag(tag_id=tag_id)
            self.operations_queue.append(("delete_existing_tag", coroutine))
            self.app.logger.info(f"{icons.CREATE} Queued: delete_existing_tag {tag_id}")
        self._schedule_auto_process()

    def queue_add_multiple_tags_to_task(self, task_id: str, tag_ids: list[str]) -> None:
        """Queue adding multiple tags to a single task."""
        for tag_id in tag_ids:
            coroutine = self.client.add_tag_to_task(
                task_id=task_id,
                tag_id_to_add=tag_id,
            )
            self.operations_queue.append(("add_tag_to_task", coroutine))
            self.app.logger.info(
                f"{icons.CREATE} Queued: add_tag_to_task {task_id}->{tag_id}",
            )
        self._schedule_auto_process()

    # ─── Direct Operations (Tags) ────────────────────────────────────────────────
    async def create_tag_now(self, tag_name: str) -> Any:
        """Create a new tag immediately."""
        return await self.call_direct("create_new_tag", tag_name=tag_name)

    async def delete_tag_now(self, tag_id: str) -> Any:
        """Delete an existing tag immediately."""
        return await self.call_direct("delete_existing_tag", tag_id=tag_id)

    async def update_tag_now(self, tag_id: str, **kwargs: Any) -> Any:
        """Update an existing tag immediately."""
        return await self.call_direct("update_existing_tag", tag_id=tag_id, **kwargs)

    async def add_tag_to_task_now(self, task_id: str, tag_id: str) -> Any:
        """Add a tag to a task immediately."""
        return await self.call_direct("add_tag_to_task", task_id=task_id, tag_id=tag_id)

    async def remove_tag_from_task_now(self, task_id: str, tag_id: str) -> Any:
        """Remove a tag from a task immediately."""
        return await self.call_direct(
            "remove_tag_from_task",
            task_id=task_id,
            tag_id=tag_id,
        )
