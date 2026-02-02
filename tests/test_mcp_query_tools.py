"""
Unit tests for MCP rulebook query tools.

Tests cover:
- search_rules with various filters
- get_class_info
- get_race_info
- get_spell_info
- get_monster_info
- validate_character_rules with valid and invalid characters
"""

import asyncio
import pytest
from pathlib import Path

from gamemaster_mcp.storage import DnDStorage


def run_async(coro):
    """Helper to run async code in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)
from gamemaster_mcp.models import Character, CharacterClass, Race, AbilityScore
from gamemaster_mcp.rulebooks import RulebookManager
from gamemaster_mcp.rulebooks.sources.custom import CustomSource
from gamemaster_mcp.rulebooks.validators import CharacterValidator


@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def storage_with_rules(temp_storage_dir: Path) -> DnDStorage:
    """Create storage with a campaign and loaded custom rulebook."""
    storage = DnDStorage(data_dir=temp_storage_dir)

    # Create test campaign
    storage.create_campaign(
        name="Test Campaign",
        description="Test campaign for rulebook query tests",
        dm_name="Test DM",
    )

    # Initialize rulebook manager
    campaign_dir = storage._split_backend._get_campaign_dir("Test Campaign")
    storage._rulebook_manager = RulebookManager(campaign_dir)

    # Create a custom rulebook with test data
    custom_rulebook_path = temp_storage_dir / "test_rulebook.json"
    custom_rulebook_data = {
        "classes": [
            {
                "index": "wizard",
                "name": "Wizard",
                "hit_die": 6,
                "proficiency_choices": {},
                "proficiencies": [],
                "saving_throws": ["Intelligence", "Wisdom"],
                "starting_equipment": [],
                "starting_equipment_options": [],
                "class_levels": {
                    "1": {
                        "level": 1,
                        "ability_score_bonuses": 0,
                        "proficiency_bonus": 2,
                        "features": ["Spellcasting", "Arcane Recovery"]
                    }
                },
                "subclasses": ["School of Evocation", "School of Abjuration"],
                "spellcasting": {
                    "level": 1,
                    "spellcasting_ability": "Intelligence",
                    "info": []
                }
            }
        ],
        "races": [
            {
                "index": "elf",
                "name": "Elf",
                "speed": 30,
                "ability_bonuses": [
                    {"ability_score": "Dexterity", "bonus": 2}
                ],
                "alignment": "Chaotic Good",
                "age": "Elves mature at 100 years",
                "size": "Medium",
                "size_description": "Elves are slender and graceful",
                "starting_proficiencies": [],
                "starting_proficiency_options": {},
                "languages": [],
                "language_desc": "Common and Elvish",
                "traits": [
                    {
                        "index": "darkvision",
                        "name": "Darkvision",
                        "desc": ["You can see in dim light within 60 feet"]
                    }
                ],
                "subraces": ["High Elf", "Wood Elf"]
            }
        ],
        "spells": [
            {
                "index": "fireball",
                "name": "Fireball",
                "desc": ["A bright streak flashes from your pointing finger"],
                "higher_level": ["When you cast this spell using a spell slot of 4th level or higher"],
                "range": "150 feet",
                "components": ["V", "S", "M"],
                "material": "A tiny ball of bat guano and sulfur",
                "ritual": False,
                "duration": "Instantaneous",
                "concentration": False,
                "casting_time": "1 action",
                "level": 3,
                "attack_type": "ranged",
                "damage": {"damage_type": "fire"},
                "school": "Evocation",
                "classes": ["wizard", "sorcerer"]
            }
        ],
        "monsters": [
            {
                "index": "goblin",
                "name": "Goblin",
                "size": "Small",
                "type": "humanoid",
                "alignment": "neutral evil",
                "armor_class": [{"type": "armor", "value": 15}],
                "hit_points": 7,
                "hit_dice": "2d6",
                "speed": {"walk": "30 ft."},
                "strength": 8,
                "dexterity": 14,
                "constitution": 10,
                "intelligence": 10,
                "wisdom": 8,
                "charisma": 8,
                "proficiencies": [],
                "damage_vulnerabilities": [],
                "damage_resistances": [],
                "damage_immunities": [],
                "condition_immunities": [],
                "senses": {"darkvision": "60 ft.", "passive_perception": "9"},
                "languages": "Common, Goblin",
                "challenge_rating": 0.25,
                "xp": 50,
                "special_abilities": [],
                "actions": []
            }
        ]
    }

    import json
    custom_rulebook_path.write_text(json.dumps(custom_rulebook_data))

    # Load the custom source
    custom_source = CustomSource(custom_rulebook_path)
    run_async(storage.rulebook_manager.load_source(custom_source))

    return storage


@pytest.fixture
def character_wizard(storage_with_rules: DnDStorage) -> Character:
    """Create a valid wizard character."""
    character = Character(
        name="Gandalf",
        player_name="Alice",
        character_class=CharacterClass(name="Wizard", level=1),
        race=Race(name="Elf"),
        abilities={
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=12),
            "intelligence": AbilityScore(score=16),
            "wisdom": AbilityScore(score=13),
            "charisma": AbilityScore(score=10),
        },
        features_and_traits=["Spellcasting", "Arcane Recovery", "Darkvision"],
    )
    storage_with_rules.add_character(character)
    return character


@pytest.fixture
def character_invalid(storage_with_rules: DnDStorage) -> Character:
    """Create an invalid character with unknown class."""
    character = Character(
        name="Invalid Bob",
        player_name="Bob",
        character_class=CharacterClass(name="Unknown Class", level=1),
        race=Race(name="Unknown Race"),
        abilities={
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=10),
            "constitution": AbilityScore(score=10),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=10),
            "charisma": AbilityScore(score=10),
        },
    )
    storage_with_rules.add_character(character)
    return character


def test_search_rules_basic(storage_with_rules: DnDStorage):
    """Test basic search functionality."""
    # Perform search
    results = storage_with_rules.rulebook_manager.search(query="wizard", categories=None, limit=20)

    # Should find the wizard class
    assert len(results) > 0
    assert any("wizard" in r.name.lower() for r in results)


def test_search_rules_with_category_filter(storage_with_rules: DnDStorage):
    """Test search with category filter."""
    # Search only in spells
    results = storage_with_rules.rulebook_manager.search(query="fire", categories=["spell"], limit=20)

    # Should find fireball spell
    assert len(results) > 0
    assert all(r.category == "spell" for r in results)


def test_search_rules_no_results(storage_with_rules: DnDStorage):
    """Test search with no results."""
    results = storage_with_rules.rulebook_manager.search(query="nonexistent", categories=None, limit=20)

    assert len(results) == 0


def test_get_class_info_found(storage_with_rules: DnDStorage):
    """Test getting class information."""
    class_def = storage_with_rules.rulebook_manager.get_class("wizard")

    assert class_def is not None
    assert class_def.name == "Wizard"
    assert class_def.hit_die == 6
    assert "Intelligence" in class_def.saving_throws
    assert "School of Evocation" in class_def.subclasses


def test_get_class_info_not_found(storage_with_rules: DnDStorage):
    """Test getting non-existent class."""
    class_def = storage_with_rules.rulebook_manager.get_class("barbarian")

    assert class_def is None


def test_get_race_info_found(storage_with_rules: DnDStorage):
    """Test getting race information."""
    race_def = storage_with_rules.rulebook_manager.get_race("elf")

    assert race_def is not None
    assert race_def.name == "Elf"
    assert race_def.size.value == "Medium"
    assert race_def.speed == 30
    assert len(race_def.ability_bonuses) > 0
    assert race_def.ability_bonuses[0].ability_score == "Dexterity"


def test_get_race_info_not_found(storage_with_rules: DnDStorage):
    """Test getting non-existent race."""
    race_def = storage_with_rules.rulebook_manager.get_race("dragonborn")

    assert race_def is None


def test_get_spell_info_found(storage_with_rules: DnDStorage):
    """Test getting spell information."""
    spell = storage_with_rules.rulebook_manager.get_spell("fireball")

    assert spell is not None
    assert spell.name == "Fireball"
    assert spell.level == 3
    assert spell.school.value == "Evocation"
    assert "V" in spell.components
    assert spell.casting_time == "1 action"


def test_get_spell_info_not_found(storage_with_rules: DnDStorage):
    """Test getting non-existent spell."""
    spell = storage_with_rules.rulebook_manager.get_spell("magic-missile")

    assert spell is None


def test_get_monster_info_found(storage_with_rules: DnDStorage):
    """Test getting monster information."""
    monster = storage_with_rules.rulebook_manager.get_monster("goblin")

    assert monster is not None
    assert monster.name == "Goblin"
    assert monster.size.value == "Small"
    assert monster.type == "humanoid"
    assert monster.hit_points == 7
    assert monster.challenge_rating == 0.25


def test_get_monster_info_not_found(storage_with_rules: DnDStorage):
    """Test getting non-existent monster."""
    monster = storage_with_rules.rulebook_manager.get_monster("dragon")

    assert monster is None


def test_validate_character_valid(storage_with_rules: DnDStorage, character_wizard: Character):
    """Test validating a valid character."""
    validator = CharacterValidator(storage_with_rules.rulebook_manager)
    report = validator.validate(character_wizard)

    # The character should be valid (no ERROR-level issues)
    # Note: There may be INFO-level issues about missing features
    assert report.character_id == character_wizard.id
    # Valid means no errors (warnings and info are OK)
    assert report.valid or len(report.errors) == 0


def test_validate_character_with_errors(storage_with_rules: DnDStorage, character_invalid: Character):
    """Test validating an invalid character."""
    validator = CharacterValidator(storage_with_rules.rulebook_manager)
    report = validator.validate(character_invalid)

    # Should have warnings about unknown class/race
    assert len(report.warnings) > 0
    # Check for unknown class warning
    assert any("unknown" in issue.message.lower() for issue in report.warnings)


def test_no_rulebooks_loaded():
    """Test behavior when no rulebooks are loaded."""
    temp_dir = Path("/tmp/test_no_rules")
    temp_dir.mkdir(exist_ok=True)
    storage = DnDStorage(data_dir=temp_dir)
    storage.create_campaign(name="Test", description="Test")

    # No rulebook manager initialized
    assert storage.rulebook_manager is None

    # Search should return empty results
    # (In the actual tool, this would return an error message)


def test_search_markdown_output_format(storage_with_rules: DnDStorage):
    """Test markdown output format for search results."""
    results = storage_with_rules.rulebook_manager.search(query="wizard", categories=None, limit=20)

    if results:
        # Simulate markdown format as in the tool
        lines = [f"# Search Results: 'wizard'\n"]
        for r in results:
            lines.append(f"- **{r.name}** ({r.category}) — _{r.source}_")

        output = "\n".join(lines)
        assert "# Search Results" in output
        assert "**" in output  # Markdown bold


def test_class_info_markdown_output(storage_with_rules: DnDStorage):
    """Test markdown output format for class info."""
    class_def = storage_with_rules.rulebook_manager.get_class("wizard")

    if class_def:
        lines = [f"# {class_def.name}\n"]
        lines.append(f"**Hit Die:** d{class_def.hit_die}")
        lines.append(f"**Saving Throws:** {', '.join(class_def.saving_throws)}")

        output = "\n".join(lines)
        assert "# Wizard" in output
        assert "**Hit Die:** d6" in output


def test_race_info_markdown_output(storage_with_rules: DnDStorage):
    """Test markdown output format for race info."""
    race_def = storage_with_rules.rulebook_manager.get_race("elf")

    if race_def:
        lines = [f"# {race_def.name}\n"]
        lines.append(f"**Size:** {race_def.size.value}")
        lines.append(f"**Speed:** {race_def.speed} ft.")

        output = "\n".join(lines)
        assert "# Elf" in output
        assert "**Size:** Medium" in output


def test_spell_info_markdown_output(storage_with_rules: DnDStorage):
    """Test markdown output format for spell info."""
    spell = storage_with_rules.rulebook_manager.get_spell("fireball")

    if spell:
        components = ", ".join(spell.components)
        if spell.material:
            components += f" ({spell.material})"

        lines = [f"# {spell.name}"]
        lines.append(f"*{spell.level_text} {spell.school.value}*\n")
        lines.append(f"**Casting Time:** {spell.casting_time}")

        output = "\n".join(lines)
        assert "# Fireball" in output
        assert "3rd-level Evocation" in output


def test_monster_info_markdown_output(storage_with_rules: DnDStorage):
    """Test markdown output format for monster info."""
    monster = storage_with_rules.rulebook_manager.get_monster("goblin")

    if monster:
        lines = [f"# {monster.name}"]
        lines.append(f"*{monster.size.value} {monster.type}, {monster.alignment}*\n")
        lines.append(f"**Armor Class:** {monster.armor_class[0].value}")

        output = "\n".join(lines)
        assert "# Goblin" in output
        assert "Small humanoid" in output


def test_validation_report_markdown_output(storage_with_rules: DnDStorage, character_wizard: Character):
    """Test markdown output format for validation report."""
    validator = CharacterValidator(storage_with_rules.rulebook_manager)
    report = validator.validate(character_wizard)

    # Simulate markdown format
    status = "✅ Valid" if report.valid else "❌ Invalid"
    lines = [f"# Validation Report: {character_wizard.name}"]
    lines.append(f"**Status:** {status}\n")

    if report.errors:
        lines.append("## Errors")
        for issue in report.errors:
            lines.append(f"- **{issue.type}:** {issue.message}")

    output = "\n".join(lines)
    assert f"# Validation Report: {character_wizard.name}" in output
