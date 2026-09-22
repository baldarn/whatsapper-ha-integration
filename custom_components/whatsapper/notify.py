"""Whatsapper platform for notify component."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from html.parser import HTMLParser

import voluptuous as vol

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
from homeassistant.helpers.aiohttp_client import async_get_clientsession


_LOGGER = logging.getLogger(__name__)

HOST_PORT = "host_port"
CONF_CHAT_ID = "chat_id"
ATTR_IMAGE = "image"
ATTR_IMAGE_TYPE = "image_type"
ATTR_IMAGE_NAME = "image_name"
ATTR_IMAGE_PATH = "image_path"

# Cache configuration
CACHE_DURATION = timedelta(minutes=15)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_CHAT_ID): vol.Coerce(str)})


class ChatListParser(HTMLParser):
    """HTML parser to extract chat information from <li> elements.
    
    Parses format: "Chat Name: chat_id@domain"
    Example: "Purple Tentacle: 31612345678@c.us"
         and "Take Over the World Taskforce: 31612345678-0987654321@g.us"
    Handles chat names containing colons.
    """

    def __init__(self):
        super().__init__()
        self.chats = {}

    def handle_starttag(self, tag, attrs):
        """Handle the start of HTML tags."""
        # We'll process in handle_data, nothing to do here
        pass

    def handle_data(self, data):
        """Parse chat data from <li> text content.
        
        Expected format: "Chat Name: chat_id"
        Split on last colon to handle names with colons.
        """
        content = data.strip()
        if not content:
            return
        
        # Split on the last colon to separate name from ID
        # This allows chat names to contain colons
        if ": " in content:
            # Find the last occurrence of ": "
            last_colon_idx = content.rfind(": ")
            chat_name = content[:last_colon_idx].strip()
            chat_id = content[last_colon_idx + 2:].strip()
            
            # Validate chat_id format (should contain @ symbol)
            if chat_id and "@" in chat_id and chat_name:
                self.chats[chat_name] = chat_id
                _LOGGER.debug("Parsed chat: '%s' -> %s", chat_name, chat_id)
        else:
            _LOGGER.debug("Skipping invalid chat format: %s", content)

    def handle_endtag(self, tag):
        """Handle the end of HTML tags."""
        # Nothing to do for end tags
        pass


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
    """Whatsapper notification service with chat target discovery."""

    def __init__(self, hass, chat_id, host_port):
        """Initialize the service."""
        self.chat_id = chat_id
        self.host_port = host_port
        self.hass = hass
        self._cached_targets = None
        self._cache_timestamp = None
    @property
    def targets(self):
        """Return a dictionary of registered chat targets.
        
        This property is called by Home Assistant to discover available
        notification targets. Returns a dict mapping chat_name -> chat_id.
        
        Note: This must be synchronous, so we return cached data or trigger
        an async fetch in the background if cache is stale.
        """
        now = datetime.now()
        
        # Return cached targets if still valid
        if (
            self._cached_targets is not None
            and self._cache_timestamp is not None
            and (now - self._cache_timestamp) < CACHE_DURATION
        ):
            return self._cached_targets

        # If cache is stale or missing, trigger background refresh
        # and return current cache (or empty dict)
        self.hass.async_create_task(self._async_refresh_targets())
        
        return self._cached_targets or {}

    async def _async_refresh_targets(self):
        """Fetch and parse chat list asynchronously."""
        try:
            session = async_get_clientsession(self.hass)
            url = f'http://{self.host_port}/chats'
            
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                html_content = await response.text()
            
            # Parse HTML to extract chat list (parsing is CPU-bound but fast)
            parser = ChatListParser()
            parser.feed(html_content)
            
            self._cached_targets = parser.chats
            self._cache_timestamp = datetime.now()
            
            _LOGGER.info(
                "Fetched %d chat targets from %s",
                len(self._cached_targets),
                url
            )

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout fetching chat list from %s", url)
        except Exception as e:
            _LOGGER.error("Failed to fetch chat list: %s", e)

    async def async_send_message(self, message="", **kwargs):
        """Send a message to the target asynchronously."""
        try:
            # Use override from notify or the one in the config
            chat_id = kwargs.get(ATTR_TARGET)
            if not chat_id:
                chat_id = self.chat_id
            
            # If target is a list, use the first one
            if isinstance(chat_id, list):
                if not chat_id:
                    _LOGGER.error("Empty target list provided")
                    return
                chat_id = chat_id[0]
            await self._async_refresh_targets()
            if chat_id in self._cached_targets:
                chat_id = self._cached_targets[chat_id]
            
            data = kwargs.get(ATTR_DATA)
            session = async_get_clientsession(self.hass)

            # Send image if path is provided
            if data and data.get(ATTR_IMAGE_PATH):
                url = f'http://{self.host_port}/command/media'
                with open(data[ATTR_IMAGE_PATH], "rb") as f:
                    requests.post(url, files={"file": f}, data={"chatId": chat_id})
                return

            # Send image if all required image data is present
            if data and all(attr in data for attr in [ATTR_IMAGE, ATTR_IMAGE_TYPE, ATTR_IMAGE_NAME]):
                url = f'http://{self.host_port}/command/media'
                body = {
                    "params": [
                        chat_id,
                        data[ATTR_IMAGE_TYPE],
                        data[ATTR_IMAGE],
                        data[ATTR_IMAGE_NAME]
                    ]
                }
                async with session.post(url, json=body, timeout=30) as response:
                    response.raise_for_status()
                _LOGGER.debug("Sent media message to %s", chat_id)
                return

            # Send text message
            title = kwargs.get(ATTR_TITLE)
            msg = f"{title}\n\n{message}" if title else message
            msg = msg.replace("\\n", "\n")
            
            url = f'http://{self.host_port}/command'
            body = {"command": "sendMessage", "params": [chat_id, msg]}
            async with session.post(url, json=body, timeout=30) as response:
                response.raise_for_status()
            _LOGGER.debug("Sent text message to %s", chat_id)

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout sending message to %s", chat_id)
        except Exception as e:
            _LOGGER.error("Sending to %s failed: %s", chat_id, e)

    def send_message(self, message="", **kwargs):
        """Send a message to the target (sync wrapper)."""
        # Run the async function in the Home Assistant event loop
        self.hass.async_create_task(self.async_send_message(message, **kwargs))
