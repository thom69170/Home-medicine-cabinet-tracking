"""The Medicine Cabinet integration."""
from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_AMOUNT,
    ATTR_CATEGORY,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_EXPIRATION_DATE,
    ATTR_LOCATION,
    ATTR_MEDICATION_ID,
    ATTR_MINIMUM_QUANTITY,
    ATTR_NAME,
    ATTR_NOTES,
    ATTR_PURPOSE,
    ATTR_QUANTITY,
    ATTR_UNIT,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_MEDICATION,
    SERVICE_CONSUME,
    SERVICE_REMOVE_MEDICATION,
    SERVICE_RESTOCK,
    SERVICE_UPDATE_MEDICATION,
)
from .coordinator import MedicineCabinetCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_URL = "/medicine_cabinet_files/medicine-cabinet-card.js"
CARD_FILENAME = "medicine-cabinet-card.js"
_FRONTEND_REGISTERED = f"{DOMAIN}_frontend_registered"

ADD_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_QUANTITY): vol.Coerce(float),
        vol.Optional(ATTR_UNIT): cv.string,
        vol.Optional(ATTR_EXPIRATION_DATE): cv.string,
        vol.Optional(ATTR_PURPOSE): cv.string,
        vol.Optional(ATTR_CATEGORY): cv.string,
        vol.Optional(ATTR_MINIMUM_QUANTITY): vol.Coerce(float),
        vol.Optional(ATTR_LOCATION): cv.string,
        vol.Optional(ATTR_NOTES): cv.string,
    }
)

UPDATE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Optional(ATTR_NAME): cv.string,
        vol.Optional(ATTR_QUANTITY): vol.Coerce(float),
        vol.Optional(ATTR_UNIT): cv.string,
        vol.Optional(ATTR_EXPIRATION_DATE): cv.string,
        vol.Optional(ATTR_PURPOSE): cv.string,
        vol.Optional(ATTR_CATEGORY): cv.string,
        vol.Optional(ATTR_MINIMUM_QUANTITY): vol.Coerce(float),
        vol.Optional(ATTR_LOCATION): cv.string,
        vol.Optional(ATTR_NOTES): cv.string,
    }
)

REMOVE_MEDICATION_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_MEDICATION_ID): cv.string,
    }
)

ADJUST_QUANTITY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_MEDICATION_ID): cv.string,
        vol.Required(ATTR_AMOUNT): vol.Coerce(float),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Medicine Cabinet from a config entry."""
    coordinator = MedicineCabinetCoordinator(hass, entry)
    await coordinator.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)
    await _async_register_frontend(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: MedicineCabinetCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.async_unload()
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_ADD_MEDICATION,
                SERVICE_UPDATE_MEDICATION,
                SERVICE_REMOVE_MEDICATION,
                SERVICE_CONSUME,
                SERVICE_RESTOCK,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and auto-inject it on every dashboard.

    Using add_extra_js_url means the card just works after installing the
    integration: no manual "resources:" entry to add in Lovelace.
    """
    if hass.data.get(_FRONTEND_REGISTERED):
        return
    hass.data[_FRONTEND_REGISTERED] = True

    card_path = Path(__file__).parent / "www" / CARD_FILENAME
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(card_path), False)]
        )
    except ImportError:
        # Home Assistant < 2024.7 does not have StaticPathConfig yet.
        hass.http.register_static_path(CARD_URL, str(card_path), cache_headers=False)

    add_extra_js_url(hass, CARD_URL)


def _get_coordinator(hass: HomeAssistant, entry_id: str) -> MedicineCabinetCoordinator:
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None:
        raise ServiceValidationError(
            f"Unknown medicine cabinet config entry: {entry_id}"
        )
    return coordinator


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    """Register the medicine_cabinet services once."""
    if hass.services.has_service(DOMAIN, SERVICE_ADD_MEDICATION):
        return

    async def handle_add(call: ServiceCall) -> None:
        data = dict(call.data)
        entry_id = data.pop(ATTR_CONFIG_ENTRY_ID)
        coordinator = _get_coordinator(hass, entry_id)
        await coordinator.async_add_medication(
            name=data[ATTR_NAME],
            quantity=data[ATTR_QUANTITY],
            unit=data.get(ATTR_UNIT),
            expiration_date=data.get(ATTR_EXPIRATION_DATE),
            purpose=data.get(ATTR_PURPOSE),
            category=data.get(ATTR_CATEGORY),
            minimum_quantity=data.get(ATTR_MINIMUM_QUANTITY),
            location=data.get(ATTR_LOCATION),
            notes=data.get(ATTR_NOTES),
        )

    async def handle_update(call: ServiceCall) -> None:
        data = dict(call.data)
        entry_id = data.pop(ATTR_CONFIG_ENTRY_ID)
        medication_id = data.pop(ATTR_MEDICATION_ID)
        coordinator = _get_coordinator(hass, entry_id)
        try:
            await coordinator.async_update_medication(medication_id, **data)
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown medication id: {medication_id}"
            ) from err

    async def handle_remove(call: ServiceCall) -> None:
        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        medication_id = call.data[ATTR_MEDICATION_ID]
        coordinator = _get_coordinator(hass, entry_id)
        try:
            await coordinator.async_remove_medication(medication_id)
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown medication id: {medication_id}"
            ) from err

    async def handle_consume(call: ServiceCall) -> None:
        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        medication_id = call.data[ATTR_MEDICATION_ID]
        amount = call.data[ATTR_AMOUNT]
        coordinator = _get_coordinator(hass, entry_id)
        try:
            await coordinator.async_adjust_quantity(medication_id, -abs(amount))
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown medication id: {medication_id}"
            ) from err

    async def handle_restock(call: ServiceCall) -> None:
        entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        medication_id = call.data[ATTR_MEDICATION_ID]
        amount = call.data[ATTR_AMOUNT]
        coordinator = _get_coordinator(hass, entry_id)
        try:
            await coordinator.async_adjust_quantity(medication_id, abs(amount))
        except KeyError as err:
            raise ServiceValidationError(
                f"Unknown medication id: {medication_id}"
            ) from err

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_MEDICATION, handle_add, schema=ADD_MEDICATION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_MEDICATION,
        handle_update,
        schema=UPDATE_MEDICATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_MEDICATION,
        handle_remove,
        schema=REMOVE_MEDICATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CONSUME, handle_consume, schema=ADJUST_QUANTITY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESTOCK, handle_restock, schema=ADJUST_QUANTITY_SCHEMA
    )
