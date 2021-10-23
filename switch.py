"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .fbee import FBee


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
        lambda d: add_entities([FBeeSwitch(d)]),
    )
    d.connect()
    d.refresh_devices()
    """Set up the switch platform."""


#    add_entities([FBeeSwitch()])


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
        """Return the state of the sensor."""
        return self.d.get_state()

    def turn_on(self, **kwargs) -> None:
        self.d.push_state(1)

    def turn_off(self, **kwargs) -> None:
        self.d.push_state(0)
