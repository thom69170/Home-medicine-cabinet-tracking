"""Config flow for the Medicine Cabinet integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_EXPIRY_WARNING_DAYS,
    CONF_LOW_STOCK_DEFAULT,
    CONF_NOTIFY_EXPIRED,
    CONF_NOTIFY_LOW_STOCK,
    DEFAULT_EXPIRY_WARNING_DAYS,
    DEFAULT_LOW_STOCK_DEFAULT,
    DEFAULT_NOTIFY_EXPIRED,
    DEFAULT_NOTIFY_LOW_STOCK,
    DOMAIN,
)

DEFAULT_CABINET_NAME = "Armoire à pharmacie"


class MedicineCabinetConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Medicine Cabinet."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Let the user name a new medicine cabinet."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input["name"].strip()
            if not name:
                errors["name"] = "name_required"
            else:
                self._async_abort_entries_match({"name": name})
                return self.async_create_entry(title=name, data={"name": name})

        schema = vol.Schema({vol.Required("name", default=DEFAULT_CABINET_NAME): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MedicineCabinetOptionsFlow(config_entry)


class MedicineCabinetOptionsFlow(OptionsFlow):
    """Handle options for an existing Medicine Cabinet entry."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_EXPIRY_WARNING_DAYS,
                    default=options.get(
                        CONF_EXPIRY_WARNING_DAYS, DEFAULT_EXPIRY_WARNING_DAYS
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(min=1, max=365, mode=NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_LOW_STOCK_DEFAULT,
                    default=options.get(
                        CONF_LOW_STOCK_DEFAULT, DEFAULT_LOW_STOCK_DEFAULT
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(min=0, max=1000, mode=NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_NOTIFY_EXPIRED,
                    default=options.get(
                        CONF_NOTIFY_EXPIRED, DEFAULT_NOTIFY_EXPIRED
                    ),
                ): BooleanSelector(),
                vol.Required(
                    CONF_NOTIFY_LOW_STOCK,
                    default=options.get(
                        CONF_NOTIFY_LOW_STOCK, DEFAULT_NOTIFY_LOW_STOCK
                    ),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
