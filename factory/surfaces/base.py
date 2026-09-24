from __future__ import annotations

from abc import ABC, abstractmethod


class Surface(ABC):
    id: str = "base"

    @abstractmethod
    def intake(self) -> dict | None: ...

    @abstractmethod
    def deliver(self, order: dict, message: str) -> dict: ...

    def receipt(self) -> dict | None:
        return None
