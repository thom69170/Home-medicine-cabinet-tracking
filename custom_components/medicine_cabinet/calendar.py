"""Calendar platform for the Medicine Cabinet integration.

Exposes each medication's expiration date as an all-day calendar event so
it shows up naturally on Home Assistant's calendar dashboard and can be
used in automations (e.g. "notify me 30 days before an event").
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTR_EXPIRATION_DATE, ATTR_PURPOSE, DOMAIN, MANUFACTURER
from .coordinator import MedicineCabinetCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the expiration calendar for a cabinet."""
    coordinator: MedicineCabinetCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MedicineExpirationCalendar(coordinator, entry)])


class MedicineExpirationCalendar(CoordinatorEntity[MedicineCabinetCoordinator], CalendarEntity):
    """Calendar of medication expiration dates."""

    _attr_has_entity_name = True
    _attr_translation_key = "expiration_calendar"
    _attr_icon = "mdi:calendar-heart"

    def __init__(
        self, coordinator: MedicineCabinetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_expiration_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="Armoire à pharmacie",
        )

    def _events(self) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        for medication in self.coordinator.medications.values():
            exp_raw = medication.get(ATTR_EXPIRATION_DATE)
            if not exp_raw:
                continue
            try:
                exp_date = date.fromisoformat(exp_raw)
            except ValueError:
                continue
            purpose = medication.get(ATTR_PURPOSE)
            description = f"Utilité : {purpose}" if purpose else None
            events.append(
                CalendarEvent(
                    start=exp_date,
                    end=exp_date + timedelta(days=1),
                    summary=f"Péremption : {medication['name']}",
                    description=description,
                )
            )
        return sorted(events, key=lambda event: event.start)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming expiration event."""
        today = dt_util.now().date()
        upcoming = [event for event in self._events() if event.start >= today]
        return upcoming[0] if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        start = dt_util.as_local(start_date).date()
        end = dt_util.as_local(end_date).date()
        return [event for event in self._events() if start <= event.start <= end]
