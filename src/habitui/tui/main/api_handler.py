# ♥♥─── Queued API Handler ──────────────────────────────────────────
# Standard Library
from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar
import asyncio
from collections.abc import Callable

from textual.message import Message

from habitui.custom_logger import log


if TYPE_CHECKING:
    from habitui.tui.main_app import HabiTUI


ClientT = TypeVar("ClientT")


class BatcherMethod:
    """Representa un método de cliente que puede ser añadido a un lote."""

    def __init__(self, batcher: HabiticaBatcher[Any], method_name: str) -> None:
        """Inicializa el método proxy.

        :param batcher: La instancia padre de HabiticaBatcher
        :param method_name: El nombre del método del cliente a representar
        """
        self.batcher = batcher
        self.method_name = method_name
        original_method: Callable[..., Any] = getattr(batcher.client, method_name)

        self.__doc__ = getattr(original_method, "__doc__", None)
        self.__annotations__ = getattr(original_method, "__annotations__", {})

    def __call__(self, *args: Any, **kwargs: Any) -> HabiticaBatcher[Any]:
        """Añade esta llamada de método al lote de ejecución."""
        return self.batcher.add(self.method_name, *args, **kwargs)


class PendingCalls(Message):
    def __init__(self, pending: int) -> None:
        self.pending = pending
        super().__init__()


class SuccessfulCalls(Message):
    def __init__(self, success_count: int, total: int) -> None:
        self.success_count = success_count
        self.total = total
        super().__init__()


class HabiticaBatcher[ClientT]:
    """Un proxy para agrupar llamadas a la API de Habitica para su ejecución."""

    def __init__(self, client: ClientT, app: HabiTUI) -> None:
        """Inicializa el agrupador de llamadas a la API.

        :param client: El cliente de la API de Habitica
        :param app: La instancia de la aplicación Textual
        """
        self.client: ClientT = client
        self.app: HabiTUI = app
        self.calls: list[tuple[str, tuple, dict[str, Any]]] = []
        self.is_executing = False
        self._execution_task: asyncio.Task[Any] | None = None

        # Debug logging
        log.info(
            f"HabiticaBatcher initialized with client: {type(client).__name__}, app: {type(app).__name__}",
        )
        log.info(f"App has post_message: {hasattr(app, 'post_message')}")

    @property
    def pending(self) -> int:
        """Devuelve el número de llamadas pendientes en el lote."""
        return len(self.calls)

    def __getattr__(self, name: str) -> BatcherMethod:
        """Hace proxy de las llamadas a métodos hacia el cliente subyacente."""
        if hasattr(self.client, name):
            return BatcherMethod(self, name)

        msg = f"'{type(self.client).__name__}' object has no attribute '{name}'"
        raise AttributeError(msg)

    def add(
        self,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HabiticaBatcher[ClientT]:
        """Añade una llamada de método al lote y programa la ejecución."""
        self.calls.append((method_name, args, kwargs))

        # Programa la ejecución sin bloquear
        if not self.is_executing:
            self._schedule_execution()

        log.info(f"Added {method_name} to batch. Pending calls: {self.pending}")
        return self

    def _schedule_execution(self) -> None:
        """Programa la ejecución del lote de forma no bloqueante."""
        if self._execution_task and not self._execution_task.done():
            log.info("Execution already in progress, skipping")
            return  # Ya hay una ejecución en progreso

        log.info("Scheduling batch execution")
        self._execution_task = asyncio.create_task(self._execute_with_error_handling())

        # Agregar callback para ver si la tarea se completa
        def on_done(task):
            if task.exception():
                log.error(f"Execution task failed: {task.exception()}")
            else:
                log.info("Execution task completed successfully")

        self._execution_task.add_done_callback(on_done)

    async def _execute_with_error_handling(self) -> None:
        """Wrapper para manejar errores en la ejecución."""
        log.info("Starting error handling wrapper")
        try:
            result = await self.execute()
            log.info(f"Execution completed with result: {result}")
        except Exception as e:
            log.error(f"Error executing batch: {e}")
            import traceback

            log.error(f"Traceback: {traceback.format_exc()}")
            # Podrías enviar un mensaje de error a la app aquí si lo deseas

    def clear(self) -> HabiticaBatcher[ClientT]:
        """Limpia todas las llamadas pendientes del lote."""
        self.calls.clear()

        return self

    async def execute(self) -> tuple[int, int]:
        """Ejecuta todas las llamadas pendientes de forma secuencial.

        :returns: Una tupla con (llamadas exitosas, total de llamadas).
        """
        log.info(
            f"Execute called. Calls: {len(self.calls)}, Is executing: {self.is_executing}",
        )

        if not self.calls:
            log.info("No calls to execute")
            return 0, 0

        if self.is_executing:
            log.info("Already executing, returning early")
            return 0, 0

        self.is_executing = True
        success_count = 0
        total = len(self.calls)
        current_calls = self.calls.copy()

        log.info(f"About to execute {total} calls")

        # Envía mensaje de inicio
        try:
            self.app.screen.post_message(PendingCalls(total))
            log.info(f"Posted PendingCalls message with {total} calls")
        except Exception as e:
            log.error(f"Failed to post PendingCalls message: {e}")

        try:
            for i, (method_name, args, kwargs) in enumerate(current_calls, 1):
                log.info(f"Executing call {i}/{total}: {method_name}")
                try:
                    method: Callable[..., Any] = getattr(self.client, method_name)
                    log.debug(
                        f"Got method {method_name}, calling with args={args}, kwargs={kwargs}",
                    )
                    result = await method(*args, **kwargs)
                    success_count += 1
                    self.app.post_message(SuccessfulCalls(success_count, total))

                    log.info(f"Call {i}/{total} ({method_name}) completed successfully")
                    log.debug(f"Result: {result}")
                except Exception as e:
                    log.error(f"Call {i}/{total} ({method_name}) failed: {e}")
                    import traceback

                    log.error(f"Traceback: {traceback.format_exc()}")

            # Envía mensaje de finalización
            try:
                self.app.screen.post_message(SuccessfulCalls(success_count, total))
                log.info(f"Posted SuccessfulCalls message: {success_count}/{total}")
            except Exception as e:
                log.error(f"Failed to post SuccessfulCalls message: {e}")

            log.info(f"Batch execution completed: {success_count}/{total} successful")

            # Limpia las llamadas ejecutadas
            self.calls = self.calls[len(current_calls) :]
            log.info(f"Remaining calls after cleanup: {len(self.calls)}")

            return success_count, total

        finally:
            self.is_executing = False
            log.info("Set is_executing to False")
