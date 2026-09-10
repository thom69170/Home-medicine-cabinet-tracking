"""Data coordinator for the Medicine Cabinet integration."""
from __future__ import annotations

import logging
import uuid
from datetime import date
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_CATEGORY,
    ATTR_DAYS_UNTIL_EXPIRATION,
    ATTR_EXPIRATION_DATE,
    ATTR_ID,
    ATTR_IS_EXPIRED,
    ATTR_IS_EXPIRING_SOON,
    ATTR_IS_LOW_STOCK,
    ATTR_LOCATION,
    ATTR_MINIMUM_QUANTITY,
    ATTR_NAME,
    ATTR_NOTES,
    ATTR_PURPOSE,
    ATTR_QUANTITY,
    ATTR_UNIT,
    CONF_EXPIRY_WARNING_DAYS,
    CONF_LOW_STOCK_DEFAULT,
    DEFAULT_EXPIRY_WARNING_DAYS,
    DEFAULT_LOW_STOCK_DEFAULT,
    DOMAIN,
    EVENT_EXPIRED,
    EVENT_EXPIRING_SOON,
    EVENT_LOW_STOCK,
    UPDATE_INTERVAL,
)
from .storage import MedicineCabinetStore

_LOGGER = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class MedicineCabinetCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Hold and refresh the state of all medications for one cabinet."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.hass = hass
        self.entry = entry
        self.store = MedicineCabinetStore(hass, entry.entry_id)
        self.medications: dict[str, dict[str, Any]] = {}
        self._new_medication_listeners: list[Callable[[str], None]] = []
        self._removed_medication_listeners: list[Callable[[str], None]] = []
        self._previously_expired: set[str] = set()
        self._previously_expiring: set[str] = set()
        self._previously_low_stock: set[str] = set()

    @property
    def expiry_warning_days(self) -> int:
        return self.entry.options.get(
            CONF_EXPIRY_WARNING_DAYS, DEFAULT_EXPIRY_WARNING_DAYS
        )

    @property
    def default_low_stock_threshold(self) -> float:
        return self.entry.options.get(
            CONF_LOW_STOCK_DEFAULT, DEFAULT_LOW_STOCK_DEFAULT
        )

    async def async_setup(self) -> None:
        """Load persisted medications and perform the first refresh.

        Refreshing through the coordinator (rather than setting the data
        directly) makes it schedule its own periodic re-run of
        ``_async_update_data`` every ``UPDATE_INTERVAL``, which is what
        keeps derived fields like "days until expiration" current without
        any external trigger.
        """
        self.medications = await self.store.async_load()
        await self.async_refresh()

    def async_unload(self) -> None:
        """Nothing to clean up: the base coordinator owns its own timer."""

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        self._recompute_all()
        return self.medications

    def add_new_medication_listener(self, listener: Callable[[str], None]) -> None:
        self._new_medication_listeners.append(listener)

    def add_removed_medication_listener(self, listener: Callable[[str], None]) -> None:
        self._removed_medication_listeners.append(listener)

    def _recompute_one(self, medication: dict[str, Any]) -> None:
        """Fill in derived attributes for a single medication in place."""
        exp_date = _parse_date(medication.get(ATTR_EXPIRATION_DATE))
        today = date.today()
        days_left: int | None = None
        is_expired = False
        is_expiring_soon = False
        if exp_date is not None:
            days_left = (exp_date - today).days
            is_expired = days_left < 0
            is_expiring_soon = not is_expired and days_left <= self.expiry_warning_days

        quantity = medication.get(ATTR_QUANTITY, 0) or 0
        minimum = medication.get(ATTR_MINIMUM_QUANTITY)
        if minimum is None:
            minimum = self.default_low_stock_threshold
        is_low_stock = quantity <= minimum

        medication[ATTR_DAYS_UNTIL_EXPIRATION] = days_left
        medication[ATTR_IS_EXPIRED] = is_expired
        medication[ATTR_IS_EXPIRING_SOON] = is_expiring_soon
        medication[ATTR_IS_LOW_STOCK] = is_low_stock

    def _recompute_all(self) -> None:
        newly_expired: set[str] = set()
        newly_expiring: set[str] = set()
        newly_low_stock: set[str] = set()

        for med_id, medication in self.medications.items():
            self._recompute_one(medication)
            if medication[ATTR_IS_EXPIRED]:
                newly_expired.add(med_id)
            if medication[ATTR_IS_EXPIRING_SOON]:
                newly_expiring.add(med_id)
            if medication[ATTR_IS_LOW_STOCK]:
                newly_low_stock.add(med_id)

        self._fire_transition_events(
            newly_expired, self._previously_expired, EVENT_EXPIRED
        )
        self._fire_transition_events(
            newly_expiring, self._previously_expiring, EVENT_EXPIRING_SOON
        )
        self._fire_transition_events(
            newly_low_stock, self._previously_low_stock, EVENT_LOW_STOCK
        )

        self._previously_expired = newly_expired
        self._previously_expiring = newly_expiring
        self._previously_low_stock = newly_low_stock

    def _fire_transition_events(
        self, current: set[str], previous: set[str], event_type: str
    ) -> None:
        for med_id in current - previous:
            medication = self.medications.get(med_id)
            if medication is None:
                continue
            self.hass.bus.async_fire(
                event_type,
                {
                    "config_entry_id": self.entry.entry_id,
                    "medication_id": med_id,
                    "name": medication.get(ATTR_NAME),
                },
            )

    async def _async_persist(self) -> None:
        await self.store.async_save(self.medications)

    async def async_add_medication(
        self,
        name: str,
        quantity: float,
        unit: str | None = None,
        expiration_date: str | None = None,
        purpose: str | None = None,
        category: str | None = None,
        minimum_quantity: float | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> str:
        """Add a new medication and return its id."""
        med_id = uuid.uuid4().hex
        medication = {
            ATTR_ID: med_id,
            ATTR_NAME: name,
            ATTR_QUANTITY: quantity,
            ATTR_UNIT: unit,
            ATTR_EXPIRATION_DATE: expiration_date,
            ATTR_PURPOSE: purpose,
            ATTR_CATEGORY: category,
            ATTR_MINIMUM_QUANTITY: minimum_quantity,
            ATTR_LOCATION: location,
            ATTR_NOTES: notes,
        }
        self._recompute_one(medication)
        self.medications[med_id] = medication
        await self._async_persist()
        self.async_set_updated_data(self.medications)
        for listener in self._new_medication_listeners:
            listener(med_id)
        return med_id

    async def async_update_medication(self, medication_id: str, **changes: Any) -> None:
        """Update fields of an existing medication."""
        medication = self.medications.get(medication_id)
        if medication is None:
            raise KeyError(medication_id)
        for key, value in changes.items():
            if value is not None:
                medication[key] = value
        self._recompute_one(medication)
        await self._async_persist()
        self.async_set_updated_data(self.medications)

    async def async_remove_medication(self, medication_id: str) -> None:
        """Remove a medication."""
        if medication_id not in self.medications:
            raise KeyError(medication_id)
        del self.medications[medication_id]
        await self._async_persist()
        self.async_set_updated_data(self.medications)
        for listener in self._removed_medication_listeners:
            listener(medication_id)

    async def async_adjust_quantity(self, medication_id: str, delta: float) -> None:
        """Add (or subtract, with a negative delta) to a medication's quantity."""
        medication = self.medications.get(medication_id)
        if medication is None:
            raise KeyError(medication_id)
        new_quantity = (medication.get(ATTR_QUANTITY, 0) or 0) + delta
        medication[ATTR_QUANTITY] = max(new_quantity, 0)
        self._recompute_one(medication)
        await self._async_persist()
        self.async_set_updated_data(self.medications)

    def find_by_name(self, name: str) -> str | None:
        """Return the id of the first medication matching name (case-insensitive)."""
        lowered = name.strip().lower()
        for med_id, medication in self.medications.items():
            if str(medication.get(ATTR_NAME, "")).strip().lower() == lowered:
                return med_id
        return None
