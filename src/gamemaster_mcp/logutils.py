"""Set up and instantiate the logger."""

import logging

logger = logging.getLogger("gamemaster-mcp")
logging.basicConfig(
    level=logging.DEBUG,
)