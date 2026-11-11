"""Sensor platform for BBVA Fondos integration."""
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_CALIFICACION,
    ATTR_CATEGORY,
    ATTR_MINIMO_INVERSION,
    ATTR_RENDIMIENTO_1A,
    ATTR_RENDIMIENTO_2A,
    ATTR_RENDIMIENTO_ANIO,
    ATTR_RENDIMIENTO_DIARIO,
    ATTR_RENDIMIENTO_MES,
    ATTR_RENDIMIENTO_SEMANAL,
    ATTR_REPORT_DATE,
    ATTR_SEGMENT,
    ATTR_SERIES,
    ATTR_TICKER,
    DOMAIN,
)
from .coordinator import BBVAFondosCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BBVA Fondos sensor entities based on a config entry."""
    coordinator: BBVAFondosCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    if coordinator.data:
        for fund_key in coordinator.data.keys():
            entities.append(BBVAFondoPrecioSensor(coordinator, entry, fund_key))
            entities.append(BBVAFondoRendimientoSensor(coordinator, entry, fund_key))

    async_add_entities(entities)

class BBVAFondoBaseSensor(CoordinatorEntity[BBVAFondosCoordinator], SensorEntity):
    """Base sensor entity for BBVA fund metrics."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BBVAFondosCoordinator,
        entry: ConfigEntry,
        fund_key: str,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.fund_key = fund_key
        ticker, _, series = fund_key.partition(":")
        self.ticker = ticker
        self.series = series

    @property
    def fund_data(self) -> Dict[str, Any]:
        """Return the dictionary data for this specific fund series."""
        return self.coordinator.data.get(self.fund_key, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Group all entities for this fund under a single logical device."""
        category = self.fund_data.get("category", "Fondo de Inversión")
        segment = self.fund_data.get("segment", "Personas Físicas")
        return DeviceInfo(
            identifiers={(DOMAIN, self.ticker)},
            name=f"BBVA Fondo {self.ticker}",
            manufacturer="BBVA México Asset Management",
            model=f"{category} ({segment})",
            sw_version="1.0.0",
        )

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return full telemetry attributes for this fund series."""
        data = self.fund_data
        return {
            ATTR_TICKER: self.ticker,
            ATTR_SERIES: self.series,
            ATTR_SEGMENT: data.get("segment"),
            ATTR_CATEGORY: data.get("category"),
            ATTR_REPORT_DATE: data.get("report_date"),
            ATTR_CALIFICACION: data.get("calificacion"),
            ATTR_MINIMO_INVERSION: data.get("minimo_inversion"),
            ATTR_RENDIMIENTO_DIARIO: data.get("rendimiento_diario"),
            ATTR_RENDIMIENTO_SEMANAL: data.get("rendimiento_semanal"),
            ATTR_RENDIMIENTO_MES: data.get("rendimiento_mes"),
            ATTR_RENDIMIENTO_ANIO: data.get("rendimiento_anio"),
            ATTR_RENDIMIENTO_1A: data.get("rendimiento_1a"),
            ATTR_RENDIMIENTO_2A: data.get("rendimiento_2a"),
        }

class BBVAFondoPrecioSensor(BBVAFondoBaseSensor):
    """Sensor tracking the unit share price in MXN."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "MXN"
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:cash-multiple"

    def __init__(self, coordinator: BBVAFondosCoordinator, entry: ConfigEntry, fund_key: str):
        super().__init__(coordinator, entry, fund_key)
        self._attr_unique_id = f"{entry.entry_id}_{fund_key}_precio"
        self._attr_name = f"Precio Serie {self.series}"

    @property
    def native_value(self) -> Optional[float]:
        return self.fund_data.get("precio")

class BBVAFondoRendimientoSensor(BBVAFondoBaseSensor):
    """Sensor tracking the 1-year annualized yield percentage."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: BBVAFondosCoordinator, entry: ConfigEntry, fund_key: str):
        super().__init__(coordinator, entry, fund_key)
        self._attr_unique_id = f"{entry.entry_id}_{fund_key}_rendimiento_1a"
        self._attr_name = f"Rendimiento 1A Serie {self.series}"

    @property
    def native_value(self) -> Optional[float]:
        return self.fund_data.get("rendimiento_1a")
