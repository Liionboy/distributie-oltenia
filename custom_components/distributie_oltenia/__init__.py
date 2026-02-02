from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from .deo import DEOPortal

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Distribuție Oltenia from a config entry."""
    
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]
    token = entry.data.get(CONF_TOKEN)

    portal = DEOPortal(email, password, token)

    # Coordinator to poll data every hour (since it's not real-time)
    async def async_update_data():
        """Fetch data from API."""
        data = await hass.async_add_executor_job(portal.get_consumption_data)
        if not data:
             # Try re-login once if failed
             await hass.async_add_executor_job(portal.login)
             data = await hass.async_add_executor_job(portal.get_consumption_data)
        
        if not data:
            raise UpdateFailed("Failed to fetch consumption data")
        
        return data

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(hours=6), # Portal data doesn't update that often
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
