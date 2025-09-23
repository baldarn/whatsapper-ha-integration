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

        data = kwargs.get(ATTR_DATA)

        try:
            if data is None:
                # send the message
                url = f'http://{self.host_port}/command'
                if ATTR_TITLE in kwargs:
                    title = kwargs.get(ATTR_TITLE)
                    # Unescape any escaped newlines in message and title
                    if title is not None:
                        msg = f"{title}\n\n{message}"
                    else:
                        msg = message
                    # Replace literal backslash-n with real newlines
                    msg = msg.replace("\\n", "\n")
                    body = {"command": "sendMessage", "params": [self.chat_id, msg]}
                resp = requests.post(url, json = body)

            # Send an image
            if data is not None and ATTR_IMAGE in data and ATTR_IMAGE_TYPE in data and ATTR_IMAGE_NAME in data:
                image = data.get(ATTR_IMAGE)
                image_type = data.get(ATTR_IMAGE_TYPE)
                image_name = data.get(ATTR_IMAGE_NAME)

                url = f'http://{self.host_port}/command/media'
                body = {"params":[self.chat_id, image_type, image, image_name]}
                resp = requests.post(url, json = body)

        except Exception as e:
            _LOGGER.error("Sending to %s failed: %s", self.chat_id, e)
