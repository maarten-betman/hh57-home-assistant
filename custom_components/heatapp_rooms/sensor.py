from __future__ import annotations

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorStateClass)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STALE_MINUTES

TEMP = dict(device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfTemperature.CELSIUS)

# key, name, value field, options
ROOM_SENSORS = [
    ("temperatuur", "Temperatuur", "temperature", TEMP),
    ("doeltemperatuur", "Doeltemperatuur", "target", TEMP),
    ("batterij", "Batterij", "battery",
     dict(device_class=SensorDeviceClass.BATTERY,
          state_class=SensorStateClass.MEASUREMENT, unit=PERCENTAGE)),
    ("status", "Status", "status", {}),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [RoomSensor(coordinator, entry, rid, *spec)
                for rid in coordinator.data["rooms"] for spec in ROOM_SENSORS]
    entities.append(HotWaterTarget(coordinator, entry))
    async_add_entities(entities)


class RoomSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, rid, key, name, field, opts):
        super().__init__(coordinator)
        self._rid, self._key, self._field = rid, key, field
        room = coordinator.data["rooms"][rid]["name"]
        self._attr_unique_id = f"{entry.entry_id}_{rid}_{key}"
        self._attr_name = name
        self._attr_device_class = opts.get("device_class")
        self._attr_state_class = opts.get("state_class")
        self._attr_native_unit_of_measurement = opts.get("unit")
        if key == "status":
            self._attr_icon = "mdi:heating-coil"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{rid}")},
            name=f"Kamer {room}", manufacturer="EbV heatapp!", model="Room")

    @property
    def _room(self):
        return self.coordinator.data["rooms"].get(self._rid, {})

    @property
    def available(self):
        if not super().available or not self._room:
            return False
        if self._key == "temperatuur":
            seen = self._room.get("last_seen_min")
            return seen is not None and seen <= STALE_MINUTES
        return True

    @property
    def native_value(self):
        return self._room.get(self._field)

    @property
    def extra_state_attributes(self):
        r = self._room
        if self._key == "temperatuur":
            return {"laatst_gezien_min": r.get("last_seen_min")}
        if self._key == "doeltemperatuur":
            return {"dag": r.get("target_day"), "nacht": r.get("target_night"),
                    "min": r.get("min"), "max": r.get("max")}
        if self._key == "status":
            return {"ontbrekende_actuatoren": r.get("missing_actuators")}
        return None


class HotWaterTarget(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Warm water doeltemperatuur"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_hot_water_target"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="heatapp",
            manufacturer="EbV heatapp!", model="Control Box")

    @property
    def native_value(self):
        return self.coordinator.data["hot_water"]["target"]

    @property
    def extra_state_attributes(self):
        hw = self.coordinator.data["hot_water"]
        return {"dag": hw["target_day"], "nacht": hw["target_night"]}
