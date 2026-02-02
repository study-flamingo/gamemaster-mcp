"""
TOON encoder utility for the D&D MCP Server.

TOON (Typed Object Notation) is a human-readable data format that provides:
- Type annotations for better clarity and validation
- More compact representation than JSON for complex nested structures
- Built-in support for datetime, UUID, and other Python types
- Improved readability for configuration and data files

This module provides a graceful fallback mechanism: if TOON encoding fails
or the library is not available, it falls back to standard JSON encoding.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("gamemaster-mcp.toon_encoder")

# Attempt to import python-toon library
# If not available, gracefully degrade to JSON-only mode
try:
    import toon
    TOON_AVAILABLE = True
    logger.debug("TOON library loaded successfully")
except ImportError:
    TOON_AVAILABLE = False
    logger.debug("TOON library not available, will use JSON fallback")


def encode_to_toon(data: Any, fallback_to_json: bool = True) -> str:
    """
    Encode data to TOON format with optional JSON fallback.

    TOON format provides type-safe serialization with better human readability
    compared to JSON. This function attempts to encode data using TOON first,
    and falls back to JSON if TOON is unavailable or encoding fails.

    Args:
        data: Any Python object that can be serialized (dict, list, str, etc.)
        fallback_to_json: If True, use JSON when TOON encoding fails or is unavailable.
                         If False, raise an error instead of falling back.

    Returns:
        String representation of the data in TOON format (or JSON if fallback is used)

    Raises:
        ImportError: If TOON is not installed and fallback_to_json is False
        Exception: If TOON encoding fails and fallback_to_json is False

    Examples:
        >>> data = {"name": "Gandalf", "level": 20, "class": "Wizard"}
        >>> encoded = encode_to_toon(data)
        >>> print(encoded)  # Will use TOON if available, JSON otherwise

        >>> # Strict mode - require TOON or fail
        >>> encoded = encode_to_toon(data, fallback_to_json=False)
    """
    if TOON_AVAILABLE:
        try:
            result = toon.encode(data)
            logger.debug("Successfully encoded data to TOON format")
            return result
        except Exception as e:
            logger.warning(f"TOON encoding failed: {e}, falling back to JSON")
            if fallback_to_json:
                return json.dumps(data, default=str, indent=2)
            raise
    elif fallback_to_json:
        logger.debug("Using JSON fallback (TOON not available)")
        return json.dumps(data, default=str, indent=2)
    else:
        raise ImportError(
            "python-toon is not installed. Install it with: pip install python-toon"
        )


def decode_from_toon(data_str: str, fallback_to_json: bool = True) -> Any:
    """
    Decode data from TOON format with optional JSON fallback.

    Attempts to decode a string from TOON format first. If TOON is unavailable
    or decoding fails, falls back to JSON decoding.

    Args:
        data_str: String containing TOON or JSON formatted data
        fallback_to_json: If True, try JSON decoding when TOON fails.
                         If False, raise an error instead of falling back.

    Returns:
        Decoded Python object (dict, list, etc.)

    Raises:
        ImportError: If TOON is not installed and fallback_to_json is False
        Exception: If both TOON and JSON decoding fail

    Examples:
        >>> toon_str = 'name: str = "Gandalf"\\nlevel: int = 20'
        >>> data = decode_from_toon(toon_str)
        >>> print(data)
        {'name': 'Gandalf', 'level': 20}
    """
    if TOON_AVAILABLE:
        try:
            result = toon.decode(data_str)
            logger.debug("Successfully decoded data from TOON format")
            return result
        except Exception as e:
            logger.warning(f"TOON decoding failed: {e}, trying JSON fallback")
            if fallback_to_json:
                # Handle empty string from TOON (empty dict)
                if not data_str or data_str.strip() == "":
                    return {}
                return json.loads(data_str)
            raise
    elif fallback_to_json:
        logger.debug("Using JSON fallback for decoding (TOON not available)")
        # Handle empty string
        if not data_str or data_str.strip() == "":
            return {}
        return json.loads(data_str)
    else:
        raise ImportError(
            "python-toon is not installed. Install it with: pip install python-toon"
        )


def is_toon_available() -> bool:
    """
    Check if TOON library is available.

    Returns:
        True if python-toon is installed and can be used, False otherwise

    Examples:
        >>> if is_toon_available():
        ...     print("TOON encoding is available")
        ... else:
        ...     print("Will use JSON fallback")
    """
    return TOON_AVAILABLE
