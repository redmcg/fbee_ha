"""The fbee integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .fbee import FBee

# List of the platforms to support.
PLATFORMS: list[str] = ["switch"]

def handle_disconnect(d):
    global reconnect
    if reconnect:
        d.connect()
        d.start_async_read(disconnect_callback = handle_disconnect)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    global reconnect
    hass.data.setdefault(DOMAIN, {})

    """Set up fbee from a config entry."""
    # Store an API object for the platforms to access
    d = FBee(entry.data["host"], entry.data["port"], entry.data["serialnumber"])

    try:
        hass.data[DOMAIN][entry.entry_id] = d
    except KeyError as exc:
        raise ConfigEntryNotReady() from exc

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    d.connect()
    if "pollinterval" in entry.data:
        i = entry.data["pollinterval"]
    else:
        i = 60
    reconnect = True
    d.start_async_read(i, handle_disconnect)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    global reconnect
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        d = hass.data[DOMAIN].pop(entry.entry_id)
        reconnect = False
        d.close()

    return unload_ok
