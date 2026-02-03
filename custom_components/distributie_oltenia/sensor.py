import re
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Distributie Oltenia sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # We iterate through the data array to find different registers
    # Typical structure is list of objects
    # We'll create sensors for known registers
    
    sensors = []
    # Data is a list of dicts. We might need to handle multiple meters if they exist?
    # For now assume one meter or create sensors for all unique meters/registers found.
    
    if isinstance(coordinator.data, list):
        for reading in coordinator.data:
            register = reading.get("REGISTER")
            serial = reading.get("SERIAL")
            
            # Create a unique ID based on serial and register
            if register and serial:
                sensors.append(DEOSensor(coordinator, reading))

    async_add_entities(sensors)


class DEOSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Distributie Oltenia Sensor."""

    def __init__(self, coordinator, reading_data):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._register = reading_data.get("REGISTER")
        self._serial = reading_data.get("SERIAL")
        self._desc = reading_data.get("REGISTER_DESC", self._register)
        
        # Use Serial + Register as unique ID
        self._attr_unique_id = f"{DOMAIN}_{self._serial}_{self._register}".replace(".", "_")
        self._attr_name = f"DEO {self._desc} {self._serial}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._serial)},
            "name": f"Contor {self._serial}",
            "manufacturer": "Distribuție Oltenia",
            "model": "Smart Meter",
        }

        # Set device class and state class
        if "Energie" in self._desc or "Producție" in self._desc or "Consum" in self._desc:
             self._attr_device_class = SensorDeviceClass.ENERGY
             self._attr_state_class = SensorStateClass.TOTAL_INCREASING
             self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        
        # Initial update
        self._update_from_data()

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Find the latest reading for this register from coordinator data
        return self._get_latest_reading()

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = self._find_my_data()
        if data:
            return {
                "reading_date": self._parse_date(data.get("READING_DATE")),
                "billing_constant": data.get("BILLING_CONSTANT"),
                "consumption": self._parse_consumption(data.get("CONSUMPTION")),
                "register_code": self._register,
                "meter_serial": self._serial,
                "reading_type": data.get("READING_TYPE"),
            }
        return {}
    
    def _parse_date(self, date_str):
        """Parse /Date(timestamp)/ format to readable date."""
        if not date_str:
            return None
        match = re.search(r'/Date\((\d+)\)/', str(date_str))
        if match:
            timestamp_ms = int(match.group(1))
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime("%Y-%m-%d")
        return date_str
    
    def _parse_consumption(self, consumption_str):
        """Parse European format consumption to float (e.g., 1.218,001 -> 1218.001)."""
        if not consumption_str:
            return None
        try:
            # Remove thousand separators (.) and replace decimal comma with dot
            cleaned = str(consumption_str).replace('.', '').replace(',', '.')
            return float(cleaned)
        except ValueError:
            return consumption_str

    def _find_my_data(self):
        """Find the data dict correspondng to this sensor in the list."""
        if isinstance(self.coordinator.data, list):
            for item in self.coordinator.data:
                if item.get("REGISTER") == self._register and item.get("SERIAL") == self._serial:
                    return item
        return None

    def _get_latest_reading(self):
        """Get the latest index value."""
        data = self._find_my_data()
        if data:
            # MRINDEX is likely the total index
            idx = data.get("MRINDEX")
            if idx:
                try:
                    return float(idx)
                except ValueError:
                    return None
        return None

    def _update_from_data(self):
        """Update internal state from data."""
        # This is called on init, but coordinator updates handle the rest
        pass
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # The sensor state is pulled from coordinator.data in native_value
        self.async_write_ha_state()
