"""Sensor platform for the Medicine Cabinet integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
    ATTR_NOTES,
    ATTR_PURPOSE,
    ATTR_UNIT,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import MedicineCabinetCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Medicine Cabinet sensors from a config entry."""
    coordinator: MedicineCabinetCoordinator = hass.data[DOMAIN][entry.entry_id]

    summary_entities = [
        MedicationCountSensor(coordinator, entry),
        MedicationExpiredCountSensor(coordinator, entry),
        MedicationExpiringSoonCountSensor(coordinator, entry),
        MedicationLowStockCountSensor(coordinator, entry),
    ]
    async_add_entities(summary_entities)

    added_entities: dict[str, MedicationSensor] = {}

    def _add_medication_entity(medication_id: str) -> None:
        entity = MedicationSensor(coordinator, entry, medication_id)
        added_entities[medication_id] = entity
        async_add_entities([entity])

    def _remove_medication_entity(medication_id: str) -> None:
        entity = added_entities.pop(medication_id, None)
        if entity is not None:
            hass.async_create_task(entity.async_remove())

    coordinator.add_new_medication_listener(_add_medication_entity)
    coordinator.add_removed_medication_listener(_remove_medication_entity)

    for medication_id in coordinator.medications:
        _add_medication_entity(medication_id)


class _CabinetEntity(CoordinatorEntity[MedicineCabinetCoordinator]):
    """Base entity tied to a cabinet's device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MedicineCabinetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="Armoire à pharmacie",
        )


class MedicationSensor(_CabinetEntity, SensorEntity):
    """Represents a single medication's quantity and metadata."""

    _attr_icon = "mdi:pill"

    def __init__(
        self,
        coordinator: MedicineCabinetCoordinator,
        entry: ConfigEntry,
        medication_id: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._medication_id = medication_id
        self._attr_unique_id = f"{entry.entry_id}_{medication_id}"

    @property
    def _medication(self) -> dict[str, Any] | None:
        return self.coordinator.medications.get(self._medication_id)

    @property
    def available(self) -> bool:
        return super().available and self._medication is not None

    @property
    def name(self) -> str | None:
        medication = self._medication
        return medication["name"] if medication else None

    @property
    def native_value(self) -> float | None:
        medication = self._medication
        if medication is None:
            return None
        return medication.get("quantity")

    @property
    def native_unit_of_measurement(self) -> str | None:
        medication = self._medication
        return medication.get(ATTR_UNIT) if medication else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        medication = self._medication
        if medication is None:
            return {}
        return {
            ATTR_ID: medication.get(ATTR_ID),
            ATTR_EXPIRATION_DATE: medication.get(ATTR_EXPIRATION_DATE),
            ATTR_PURPOSE: medication.get(ATTR_PURPOSE),
            ATTR_CATEGORY: medication.get(ATTR_CATEGORY),
            ATTR_MINIMUM_QUANTITY: medication.get(ATTR_MINIMUM_QUANTITY),
            ATTR_LOCATION: medication.get(ATTR_LOCATION),
            ATTR_NOTES: medication.get(ATTR_NOTES),
            ATTR_DAYS_UNTIL_EXPIRATION: medication.get(ATTR_DAYS_UNTIL_EXPIRATION),
            ATTR_IS_EXPIRED: medication.get(ATTR_IS_EXPIRED),
            ATTR_IS_EXPIRING_SOON: medication.get(ATTR_IS_EXPIRING_SOON),
            ATTR_IS_LOW_STOCK: medication.get(ATTR_IS_LOW_STOCK),
        }

    @property
    def icon(self) -> str:
        medication = self._medication
        if medication and medication.get(ATTR_IS_EXPIRED):
            return "mdi:pill-off"
        if medication and medication.get(ATTR_IS_LOW_STOCK):
            return "mdi:pill-multiple"
        return "mdi:pill"


class MedicationCountSensor(_CabinetEntity, SensorEntity):
    """Total number of medications tracked in this cabinet."""

    _attr_translation_key = "total_medications"
    _attr_icon = "mdi:medical-bag"
    _attr_native_unit_of_measurement = "médicaments"

    def __init__(
        self, coordinator: MedicineCabinetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_total"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.medications)


class MedicationExpiredCountSensor(_CabinetEntity, SensorEntity):
    """Number of expired medications."""

    _attr_translation_key = "expired_medications"
    _attr_icon = "mdi:calendar-remove"
    _attr_native_unit_of_measurement = "médicaments"

    def __init__(
        self, coordinator: MedicineCabinetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_expired"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for medication in self.coordinator.medications.values()
            if medication.get(ATTR_IS_EXPIRED)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "medications": [
                medication["name"]
                for medication in self.coordinator.medications.values()
                if medication.get(ATTR_IS_EXPIRED)
            ]
        }


class MedicationExpiringSoonCountSensor(_CabinetEntity, SensorEntity):
    """Number of medications expiring soon."""

    _attr_translation_key = "expiring_soon_medications"
    _attr_icon = "mdi:calendar-alert"
    _attr_native_unit_of_measurement = "médicaments"

    def __init__(
        self, coordinator: MedicineCabinetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_expiring_soon"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for medication in self.coordinator.medications.values()
            if medication.get(ATTR_IS_EXPIRING_SOON)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "medications": [
                medication["name"]
                for medication in self.coordinator.medications.values()
                if medication.get(ATTR_IS_EXPIRING_SOON)
            ]
        }


class MedicationLowStockCountSensor(_CabinetEntity, SensorEntity):
    """Number of medications running low."""

    _attr_translation_key = "low_stock_medications"
    _attr_icon = "mdi:tray-alert"
    _attr_native_unit_of_measurement = "médicaments"

    def __init__(
        self, coordinator: MedicineCabinetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_low_stock"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for medication in self.coordinator.medications.values()
            if medication.get(ATTR_IS_LOW_STOCK)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "medications": [
                medication["name"]
                for medication in self.coordinator.medications.values()
                if medication.get(ATTR_IS_LOW_STOCK)
            ]
        }
