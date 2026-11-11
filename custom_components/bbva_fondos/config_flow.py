"""Config flow and Options flow for BBVA Fondos integration."""
import logging
from typing import Any, Dict, Optional
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_URL,
    CONF_MODE,
    CONF_MODE_API,
    CONF_MODE_DIRECT,
    CONF_TRACKED_FUNDS,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_API_URL,
    DEFAULT_MODE,
    DEFAULT_TRACKED_FUNDS,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class BBVAFondosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BBVA Fondos."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Parse comma-separated list of funds into array
            raw_funds = user_input.get(CONF_TRACKED_FUNDS, "")
            if isinstance(raw_funds, str):
                funds_list = [f.strip().upper() for f in raw_funds.split(",") if f.strip()]
            else:
                funds_list = raw_funds or DEFAULT_TRACKED_FUNDS

            user_input[CONF_TRACKED_FUNDS] = funds_list
            return self.async_create_entry(
                title="BBVA Fondos de Inversión",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=DEFAULT_MODE): vol.In(
                    {
                        CONF_MODE_DIRECT: "Descarga directa de PDF (Recomendado, autónomo)",
                        CONF_MODE_API: "Conectar a servicio REST local/externo",
                    }
                ),
                vol.Optional(CONF_API_URL, default=DEFAULT_API_URL): str,
                vol.Required(
                    CONF_TRACKED_FUNDS,
                    default=", ".join(DEFAULT_TRACKED_FUNDS),
                ): str,
                vol.Required(
                    CONF_UPDATE_INTERVAL_HOURS,
                    default=DEFAULT_UPDATE_INTERVAL_HOURS,
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=48)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return BBVAFondosOptionsFlowHandler(config_entry)


class BBVAFondosOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow to update tracked funds without re-installing."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            raw_funds = user_input.get(CONF_TRACKED_FUNDS, "")
            if isinstance(raw_funds, str):
                funds_list = [f.strip().upper() for f in raw_funds.split(",") if f.strip()]
            else:
                funds_list = raw_funds

            user_input[CONF_TRACKED_FUNDS] = funds_list

            # Update entry data
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **user_input},
            )
            return self.async_create_entry(title="", data=user_input)

        current_funds = self.config_entry.data.get(CONF_TRACKED_FUNDS, DEFAULT_TRACKED_FUNDS)
        current_funds_str = ", ".join(current_funds) if isinstance(current_funds, list) else str(current_funds)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TRACKED_FUNDS,
                        default=current_funds_str,
                    ): str,
                    vol.Required(
                        CONF_UPDATE_INTERVAL_HOURS,
                        default=self.config_entry.data.get(
                            CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=48)),
                }
            ),
        )
