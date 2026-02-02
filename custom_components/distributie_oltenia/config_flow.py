import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, CONF_TOKEN
from .deo import DEOPortal

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_TOKEN): str,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Distribuție Oltenia."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate credentials
                valid = await self.hass.async_add_executor_job(
                    self._validate_input, user_input
                )
                
                if valid:
                    return self.async_create_entry(
                        title=user_input[CONF_EMAIL], data=user_input
                    )
                else:
                    errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    def _validate_input(self, data):
        """Validate the user input allows us to connect."""
        portal = DEOPortal(data[CONF_EMAIL], data[CONF_PASSWORD], data.get(CONF_TOKEN))
        if not portal.login():
            return False
            
        # If token is not provided, try to fetch it to ensure we can
        # If it returns None, we might still proceed but warn? 
        # For now, just login success is enough to create entry.
        return True
