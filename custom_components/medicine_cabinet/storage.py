"""Persistent storage helper for the Medicine Cabinet integration."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_PREFIX, STORAGE_VERSION


class MedicineCabinetStore:
    """Wrap a Home Assistant Store to persist one cabinet's medications."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}_{entry_id}"
        )

    async def async_load(self) -> dict[str, dict[str, Any]]:
        """Load medications keyed by id from disk."""
        data = await self._store.async_load()
        if not data:
            return {}
        return data.get("medications", {})

    async def async_save(self, medications: dict[str, dict[str, Any]]) -> None:
        """Persist medications to disk."""
        await self._store.async_save({"medications": medications})
