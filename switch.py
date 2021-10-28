"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .fbee import STATE_NEW_DEV, STATE_NEW_STATE, FBee


def callback(add_entities, d, s):
    if s & STATE_NEW_DEV:
        d.ha = FBeeSwitch(d)
        add_entities([d.ha])
    elif s & STATE_NEW_STATE:
        d.ha.schedule_update_ha_state()


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    d = FBee(
        config["host"],
        config["port"],
        config["serialnumber"],
        lambda d, s: callback(add_entities, d, s),
    )
    d.connect()
    if "pollinterval" in config:
        i = config["pollinterval"]
    else:
        i = 60
    d.start_async_read(i)
    """Set up the switch platform."""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    d = hass.data[DOMAIN][entry.entry_id]
    d.add_callback([lambda d, s: callback(async_add_entities, d, s)])


class FBeeSwitch(SwitchEntity):
    """Representation of a Switch."""

    def __init__(self, d):
        """Initialize the switch."""
        self.d = d

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self.d.get_name()

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return self.d.get_state()

    @property
    def should_poll(self) -> bool:
        """Return if we should poll."""
        return False

    @property
    def unique_id(self) -> str:
        return self.d.get_key()

    def turn_on(self, **kwargs) -> None:
        self.d.push_state(1)

    def turn_off(self, **kwargs) -> None:
        self.d.push_state(0)
