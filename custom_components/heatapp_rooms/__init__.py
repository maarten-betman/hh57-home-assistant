"""heatapp! rooms: read-only room temperatures from an EbV Gateway + Control Box."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HeatappBox, fetch_rooms
from .const import (CONF_CB_HOST, CONF_CB_PASS, CONF_CB_USER, CONF_GW_HOST,
                    CONF_GW_PASS, CONF_GW_USER, DOMAIN, SCAN_MINUTES)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


def make_boxes(hass: HomeAssistant, d: dict) -> tuple[HeatappBox, HeatappBox]:
    session = async_create_clientsession(hass)
    gw = HeatappBox(session, d[CONF_GW_HOST], d[CONF_GW_USER], d[CONF_GW_PASS], True)
    cb = HeatappBox(session, d[CONF_CB_HOST], d[CONF_CB_USER], d[CONF_CB_PASS], False)
    return gw, cb


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    gw, cb = make_boxes(hass, entry.data)

    async def update():
        try:
            return await fetch_rooms(gw, cb)
        except Exception as err:  # noqa: BLE001 - any box error = failed poll
            raise UpdateFailed(str(err)) from err

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name=DOMAIN, update_method=update,
        update_interval=timedelta(minutes=SCAN_MINUTES))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
