"""BBVA México Fondos de Inversión custom component for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import BBVAFondosCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BBVA Fondos from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = BBVAFondosCoordinator(hass, entry.data)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register custom service to trigger manual sync from HA automations
    async def handle_manual_sync(call: ServiceCall) -> None:
        """Handle execution of bbva_fondos.sync service."""
        _LOGGER.info("Manual synchronization triggered via Home Assistant service call")
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, "sync"):
        hass.services.async_register(DOMAIN, "sync", handle_manual_sync)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a BBVA Fondos config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
