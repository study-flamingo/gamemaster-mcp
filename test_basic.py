"""
Test file for the D&D MCP Server (FastMCP 2.8.0+ compliant).
"""

import pytest
from gamemaster_mcp.main import mcp
from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import Character, CharacterClass, Race, AbilityScore


def test_mcp_server_initialization():
    """Test that the FastMCP server initializes correctly."""
    assert mcp.name == "D&D Campaign Manager"
    assert "pydantic>=2.0.0" in mcp.dependencies


def test_storage_initialization():
    """Test that storage initializes correctly."""
    storage = DnDStorage("test_data")
    assert storage.data_dir.name == "test_data"


def test_character_model():
    """Test character model creation."""
    character = Character(
        name="Test Character",
        character_class=CharacterClass(name="Fighter", level=1),
        race=Race(name="Human"),
        abilities={
            "strength": AbilityScore(score=15),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=13),
            "intelligence": AbilityScore(score=12),
            "wisdom": AbilityScore(score=10),
            "charisma": AbilityScore(score=8),
        }
    )
    
    assert character.name == "Test Character"
    assert character.character_class.name == "Fighter"
    assert character.character_class.level == 1
    assert character.abilities["strength"].score == 15
    assert character.abilities["strength"].modifier == 2  # (15-10)//2 = 2


def test_ability_score_modifier():
    """Test ability score modifier calculation."""
    # Test various scores
    test_cases = [
        (1, -5),    # Score 1 -> modifier -5
        (8, -1),    # Score 8 -> modifier -1  
        (10, 0),    # Score 10 -> modifier 0
        (11, 0),    # Score 11 -> modifier 0
        (12, 1),    # Score 12 -> modifier 1
        (15, 2),    # Score 15 -> modifier 2
        (20, 5),    # Score 20 -> modifier 5
        (30, 10),   # Score 30 -> modifier 10
    ]
    
    for score, expected_modifier in test_cases:
        ability = AbilityScore(score=score)
        assert ability.modifier == expected_modifier, f"Score {score} should have modifier {expected_modifier}, got {ability.modifier}"


if __name__ == "__main__":
    pytest.main([__file__])
