# -*- coding: UTF-8 -*-
import logging

from homeassistant.components.cover import CoverDevice, SUPPORT_CLOSE, SUPPORT_OPEN
from homeassistant.const import CONF_HOST, CONF_PORT

from .util import slugify_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Platform uses config entry setup."""
    pass


async def async_setup_entry(hass, entry, async_add_entities):
    from .const import DOMAIN, DOMAIN_LISTENER
    from pydigitalstrom.devices.scene import DSColorScene

    device_slug = slugify_entry(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])

    client = hass.data[DOMAIN][device_slug]
    listener = hass.data[DOMAIN][DOMAIN_LISTENER][device_slug]
    devices = []
    scenes = client.get_scenes()
    for scene in scenes.values():
        # only handle cover (color 2) scenes
        if not isinstance(scene, DSColorScene) or scene.color != 2:
            continue
        # not an area or broadcast turn off scene
        if scene.scene_id > 4:
            continue

        # get turn on counterpart
        scene_on = scenes.get(
            "{zone_id}_{color}_{scene_id}".format(
                zone_id=scene.zone_id, color=scene.color, scene_id=scene.scene_id + 5
            ),
            None,
        )

        # no turn on scene found, skip
        if not scene_on:
            continue

        # add cover
        _LOGGER.info("adding cover {}: {}".format(scene.scene_id, scene.name))
        devices.append(
            DigitalstromCover(
                hass=hass, scene_on=scene_on, scene_off=scene, listener=listener
            )
        )

    async_add_entities(device for device in devices)


class DigitalstromCover(CoverDevice):
    def __init__(self, hass, scene_on, scene_off, listener, *args, **kwargs):
        self._hass = hass
        self._scene_on = scene_on
        self._scene_off = scene_off
        self._listener = listener
        self._state = None
        super().__init__(*args, **kwargs)

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE

    @property
    def name(self):
        return self._scene_off.name

    @property
    def unique_id(self):
        return "dscover_{id}".format(id=self._scene_off.unique_id)

    @property
    def available(self):
        return True

    @property
    def is_closed(self):
        return None

    async def async_open_cover(self, **kwargs):
        _LOGGER.info("calling cover scene {}".format(self._scene_on.scene_id))
        await self._scene_on.turn_on()

    async def async_close_cover(self, **kwargs):
        _LOGGER.info("calling cover scene {}".format(self._scene_off.scene_id))
        await self._scene_off.turn_on()

    def should_poll(self):
        return False
