"""Whatsapper platform for notify component."""
from __future__ import annotations

import logging

import voluptuous as vol

import requests

from homeassistant.components.notify import (
    PLATFORM_SCHEMA,
    BaseNotificationService,
    ATTR_DATA,
    ATTR_TITLE,
    ATTR_MESSAGE,
    ATTR_TARGET,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


_LOGGER = logging.getLogger(__name__)

HOST_PORT = "host_port"
CONF_CHAT_ID = "chat_id"
ATTR_IMAGE = "image"
ATTR_IMAGE_TYPE = "image_type"
ATTR_IMAGE_NAME = "image_name"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_CHAT_ID): vol.Coerce(str)})

def get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> WhatsapperNotificationService:
    """Get the Whatsapper notification service."""

    chat_id = config.get(CONF_CHAT_ID)
    host_port = config.get(HOST_PORT)

    if host_port is None:
        host_port = "localhost:4000"

    return WhatsapperNotificationService(hass, chat_id, host_port)

class WhatsapperNotificationService(BaseNotificationService):

    def __init__(self, hass, chat_id, host_port):
        """Initialize the service."""
        self.chat_id = chat_id
        self.host_port = host_port
        self.hass = hass

    def send_message(self, message="", **kwargs):
        """Send a message to the target."""
        try:
            # Use override from notify or the one in the config
            chat_id = kwargs.get(ATTR_TARGET) if kwargs.get(ATTR_TARGET) else self.chat_id
            data = kwargs.get(ATTR_DATA)

            # Send image if all required image data is present
            if data and all(attr in data for attr in [ATTR_IMAGE, ATTR_IMAGE_TYPE, ATTR_IMAGE_NAME]):
                url = f'http://{self.host_port}/command/media'
                body = {"params": [chat_id, data[ATTR_IMAGE_TYPE], data[ATTR_IMAGE], data[ATTR_IMAGE_NAME]]}
                requests.post(url, json=body)
                return

            # Send text message
            title = kwargs.get(ATTR_TITLE)
            msg = f"{title}\n\n{message}" if title else message
            msg = msg.replace("\\n", "\n")
            
            url = f'http://{self.host_port}/command'
            body = {"command": "sendMessage", "params": [chat_id, msg]}
            requests.post(url, json=body)

        except Exception as e:
            _LOGGER.error("Sending to %s failed: %s", chat_id, e)

