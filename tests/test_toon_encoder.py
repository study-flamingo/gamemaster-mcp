"""
Comprehensive unit tests for TOON encoder utility.

Tests cover:
- TOON encoding/decoding with library available
- JSON fallback when TOON is unavailable
- Error handling and edge cases
- Type safety and data preservation
"""

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Import toon_encoder directly to avoid loading main.py
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from gamemaster_mcp import toon_encoder


# Test fixtures for common data structures
@pytest.fixture
def simple_dict() -> dict[str, Any]:
    """Simple dictionary test data."""
    return {
        "name": "Gandalf",
        "level": 20,
        "class": "Wizard",
        "alive": True,
    }


@pytest.fixture
def nested_dict() -> dict[str, Any]:
    """Nested dictionary test data."""
    return {
        "character": {
            "name": "Aragorn",
            "stats": {
                "strength": 18,
                "dexterity": 15,
                "constitution": 16,
            },
            "inventory": ["sword", "bow", "healing potion"],
        },
        "campaign": "Lord of the Rings",
    }


@pytest.fixture
def list_data() -> list[dict[str, Any]]:
    """List of dictionaries test data."""
    return [
        {"name": "Frodo", "race": "Hobbit"},
        {"name": "Sam", "race": "Hobbit"},
        {"name": "Legolas", "race": "Elf"},
    ]


class TestToonEncoderWithLibrary:
    """Tests for TOON encoder when python-toon library is available."""

    def test_encode_simple_dict(self, simple_dict: dict[str, Any]) -> None:
        """Test encoding a simple dictionary to TOON format."""
        if not toon_encoder.TOON_AVAILABLE:
            pytest.skip("python-toon not installed")

        result = toon_encoder.encode_to_toon(simple_dict)
        assert isinstance(result, str)
        assert len(result) > 0
        # TOON output should contain the data
        assert "Gandalf" in result or "gandalf" in result.lower()

    def test_encode_nested_dict(self, nested_dict: dict[str, Any]) -> None:
        """Test encoding a nested dictionary to TOON format."""
        if not toon_encoder.TOON_AVAILABLE:
            pytest.skip("python-toon not installed")

        result = toon_encoder.encode_to_toon(nested_dict)
        assert isinstance(result, str)
        assert "Aragorn" in result or "aragorn" in result.lower()

    def test_encode_list(self, list_data: list[dict[str, Any]]) -> None:
        """Test encoding a list to TOON format."""
        if not toon_encoder.TOON_AVAILABLE:
            pytest.skip("python-toon not installed")

        result = toon_encoder.encode_to_toon(list_data)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_decode_roundtrip(self, simple_dict: dict[str, Any]) -> None:
        """Test that encoding and decoding preserves data."""
        if not toon_encoder.TOON_AVAILABLE:
            pytest.skip("python-toon not installed")

        encoded = toon_encoder.encode_to_toon(simple_dict)
        decoded = toon_encoder.decode_from_toon(encoded)
        assert decoded == simple_dict

    def test_is_toon_available(self) -> None:
        """Test the availability check function."""
        # Should return a boolean
        result = toon_encoder.is_toon_available()
        assert isinstance(result, bool)


class TestToonEncoderFallback:
    """Tests for JSON fallback behavior when TOON fails or is unavailable."""

    def test_json_fallback_when_toon_unavailable(
        self, simple_dict: dict[str, Any]
    ) -> None:
        """Test that JSON fallback works when TOON library is not available."""
        # Mock TOON as unavailable
        with patch.object(toon_encoder, "TOON_AVAILABLE", False):
            result = toon_encoder.encode_to_toon(simple_dict, fallback_to_json=True)
            # Should be valid JSON
            parsed = json.loads(result)
            assert parsed == simple_dict

    def test_json_fallback_disabled_raises_error(
        self, simple_dict: dict[str, Any]
    ) -> None:
        """Test that disabling fallback raises ImportError when TOON unavailable."""
        with patch.object(toon_encoder, "TOON_AVAILABLE", False):
            with pytest.raises(ImportError, match="python-toon is not installed"):
                toon_encoder.encode_to_toon(simple_dict, fallback_to_json=False)

    def test_decode_json_fallback(self, simple_dict: dict[str, Any]) -> None:
        """Test that decode falls back to JSON when TOON unavailable."""
        json_str = json.dumps(simple_dict)

        with patch.object(toon_encoder, "TOON_AVAILABLE", False):
            result = toon_encoder.decode_from_toon(json_str, fallback_to_json=True)
            assert result == simple_dict

    def test_decode_fallback_disabled_raises_error(self) -> None:
        """Test that disabling decode fallback raises ImportError."""
        json_str = '{"test": "data"}'

        with patch.object(toon_encoder, "TOON_AVAILABLE", False):
            with pytest.raises(ImportError, match="python-toon is not installed"):
                toon_encoder.decode_from_toon(json_str, fallback_to_json=False)


class TestToonEncoderEdgeCases:
    """Tests for edge cases and error handling."""

    def test_encode_empty_dict(self) -> None:
        """Test encoding an empty dictionary."""
        result = toon_encoder.encode_to_toon({})
        assert isinstance(result, str)
        # Should decode back to empty dict (use TOON decoder if available)
        decoded = toon_encoder.decode_from_toon(result)
        assert decoded == {}

    def test_encode_empty_list(self) -> None:
        """Test encoding an empty list."""
        result = toon_encoder.encode_to_toon([])
        assert isinstance(result, str)
        # Should decode back to empty list (use TOON decoder if available)
        decoded = toon_encoder.decode_from_toon(result)
        assert decoded == []

    def test_encode_none(self) -> None:
        """Test encoding None value."""
        result = toon_encoder.encode_to_toon(None)
        assert isinstance(result, str)

    def test_encode_special_characters(self) -> None:
        """Test encoding data with special characters."""
        data = {
            "name": "D'Artagnan",
            "description": 'He said, "Hello!"',
            "unicode": "🧙‍♂️ Wizard",
        }
        result = toon_encoder.encode_to_toon(data)
        assert isinstance(result, str)

    def test_encode_numeric_types(self) -> None:
        """Test encoding various numeric types."""
        data = {
            "integer": 42,
            "float": 3.14159,
            "negative": -100,
            "zero": 0,
        }
        result = toon_encoder.encode_to_toon(data)
        assert isinstance(result, str)

    def test_encode_with_datetime_fallback(self) -> None:
        """Test encoding datetime objects using default=str fallback."""
        from datetime import datetime

        data = {
            "timestamp": datetime(2025, 1, 1, 12, 0, 0),
            "name": "Test Event",
        }
        result = toon_encoder.encode_to_toon(data)
        assert isinstance(result, str)
        assert "Test Event" in result or "test event" in result.lower()


class TestToonEncoderErrorHandling:
    """Tests for error handling in TOON encoder."""

    def test_encode_handles_toon_exception(self) -> None:
        """Test that TOON encoding exceptions are caught and fallback works."""
        if not toon_encoder.TOON_AVAILABLE:
            pytest.skip("TOON not installed, cannot test exception handling")

        # Mock toon.encode to raise an exception
        with patch("toon.encode", side_effect=ValueError("TOON encoding error")):
            # Should fall back to JSON without raising
            result = toon_encoder.encode_to_toon({"test": "data"}, fallback_to_json=True)
            assert isinstance(result, str)
            parsed = json.loads(result)
            assert parsed == {"test": "data"}

    def test_encode_reraises_exception_when_no_fallback(self) -> None:
        """Test that exceptions are re-raised when fallback is disabled."""
        if not toon_encoder.TOON_AVAILABLE:
            pytest.skip("TOON not installed, cannot test exception handling")

        # Mock toon.encode to raise an exception
        with patch("toon.encode", side_effect=ValueError("TOON encoding error")):
            with pytest.raises(ValueError, match="TOON encoding error"):
                toon_encoder.encode_to_toon({"test": "data"}, fallback_to_json=False)

    def test_decode_handles_invalid_json(self) -> None:
        """Test that decode handles invalid JSON gracefully."""
        if toon_encoder.TOON_AVAILABLE:
            # If TOON is available, it might handle this differently
            pytest.skip("Test only for JSON fallback mode")

        invalid_json = "{ this is not valid json }"

        with pytest.raises(json.JSONDecodeError):
            toon_encoder.decode_from_toon(invalid_json, fallback_to_json=True)


class TestToonEncoderIntegration:
    """Integration tests for real-world D&D campaign data."""

    def test_encode_character_data(self) -> None:
        """Test encoding realistic character data."""
        character = {
            "id": "abc12345",
            "name": "Thorin Oakenshield",
            "race": "Dwarf",
            "class": "Fighter",
            "level": 10,
            "hp": 95,
            "max_hp": 95,
            "stats": {
                "strength": 18,
                "dexterity": 12,
                "constitution": 16,
                "intelligence": 10,
                "wisdom": 13,
                "charisma": 14,
            },
            "equipment": ["Warhammer +2", "Plate Armor", "Shield"],
            "background": "Noble",
        }

        result = toon_encoder.encode_to_toon(character)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_encode_campaign_metadata(self) -> None:
        """Test encoding campaign metadata."""
        campaign = {
            "name": "The Lost Mines",
            "dm_name": "Alice",
            "description": "A quest to reclaim the lost mines of Phandelver",
            "session_count": 5,
            "active_players": ["Bob", "Carol", "Dave"],
        }

        result = toon_encoder.encode_to_toon(campaign)
        assert isinstance(result, str)
        assert "Lost Mines" in result or "lost mines" in result.lower()
