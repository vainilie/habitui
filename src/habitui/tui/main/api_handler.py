# ♥♥─── Queued API Handler ──────────────────────────────────────────
# Standard Library
from __future__ import annotations

from typing import Any, Generic, TypeVar
import asyncio
from collections.abc import Callable


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


class HabiticaBatcher(Generic[ClientT]):
    """Un proxy para agrupar llamadas a la API de Habitica para su ejecución."""

    def __init__(self, client: ClientT):
        """Inicializa el agrupador de llamadas a la API."""
        self.client: ClientT = client
        self.calls: list[tuple[str, tuple, dict[str, Any]]] = []
        self.is_executing = False

    def __getattr__(self, name: str) -> BatcherMethod:
        """Hace proxy de las llamadas a métodos hacia el cliente subyacente."""
        if hasattr(self.client, name):
            return BatcherMethod(self, name)

        raise AttributeError(
            f"'{type(self.client).__name__}' object has no attribute '{name}'",
        )

    def add(
        self,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> HabiticaBatcher[ClientT]:
        """Añade una llamada de método al lote y programa la ejecución."""
        self.calls.append((method_name, args, kwargs))
        asyncio.create_task(self.execute())

        return self

    @property
    def pending(self) -> int:
        """Devuelve el número de llamadas pendientes en el lote."""
        return len(self.calls)

    def clear(self) -> HabiticaBatcher[ClientT]:
        """Limpia todas las llamadas pendientes del lote."""
        self.calls.clear()

        return self

    async def execute(self) -> list[Any]:
        """Ejecuta todas las llamadas pendientes de forma secuencial.

        :returns: Una lista de resultados de las llamadas a la API.
        """
        if not self.calls or self.is_executing:
            return []

        self.is_executing = True
        current_calls = self.calls.copy()
        self.calls.clear()

        try:
            results = []

            for method_name, args, kwargs in current_calls:
                method: Callable[..., Any] = getattr(self.client, method_name)
                result = await method(*args, **kwargs)
                results.append(result)

            return results
        finally:
            self.is_executing = False

    async def execute_concurrent(self) -> list[Any]:
        """Ejecuta todas las llamadas pendientes de forma concurrente.

        :returns: Una lista de resultados de las llamadas a la API.
        """
        if not self.calls or self.is_executing:
            return []

        self.is_executing = True
        current_calls = self.calls.copy()
        self.calls.clear()

        try:
            tasks = [
                getattr(self.client, method_name)(*args, **kwargs)
                for method_name, args, kwargs in current_calls
            ]

            return await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            self.is_executing = False
