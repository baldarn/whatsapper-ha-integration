"""Whatsapper platform for notify component."""
from __future__ import annotations

import logging

import voluptuous as vol

import requests

from homeassistant.components.notify import (
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType


_LOGGER = logging.getLogger(__name__)

HOST_PORT = "host_port"
CONF_CHAT_ID = "chat_id"

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
            # Actually send the message
            url = f'http://{self.host_port}/command'
            body = {"command":"sendMessage", "params":[self.chat_id, message]}
            resp = requests.post(url, json = body)
            print(resp.text)
        except Exception as e:
            _LOGGER.error("Sending to %s failed: %s", self._chat_id, e)
