from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from . import make_boxes
from .api import fetch_rooms
from .const import (CONF_CB_HOST, CONF_CB_PASS, CONF_CB_USER, CONF_GW_HOST,
                    CONF_GW_PASS, CONF_GW_USER, DOMAIN)

SCHEMA = vol.Schema({
    vol.Required(CONF_GW_HOST, default="192.168.2.2"): str,
    vol.Required(CONF_GW_USER, default="gateway"): str,
    vol.Required(CONF_GW_PASS): str,
    vol.Required(CONF_CB_HOST, default="192.168.2.3"): str,
    vol.Required(CONF_CB_USER): str,
    vol.Required(CONF_CB_PASS): str,
})


class HeatappRoomsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_CB_HOST])
            self._abort_if_unique_id_configured()
            try:
                await fetch_rooms(*make_boxes(self.hass, user_input))
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="heatapp! rooms", data=user_input)
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
