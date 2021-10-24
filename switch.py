"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .fbee import FBee

def callback(add_entities, d, n):
    if n:
        d.ha = FBeeSwitch(d)
        add_entities([d.ha])
    else:
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
        lambda d, n: callback(add_entities, d, n))
    d.connect()
    if "poll_interval" in config:
        i = config["poll_interval"]
    else:
        i = 15
    d.start_async_read(i)
    """Set up the switch platform."""


class FBeeSwitch(SwitchEntity):
    """Representation of a Switch."""

    def __init__(self, d):
        """Initialize the switch."""
        self.d = d

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self.d.name

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return self.d.get_state()

    @property
    def should_poll(self) -> bool:
        """Return if we should poll."""
        return False

    def turn_on(self, **kwargs) -> None:
        self.d.push_state(1)

    def turn_off(self, **kwargs) -> None:
        self.d.push_state(0)
