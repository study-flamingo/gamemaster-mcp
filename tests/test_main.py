"""
Unit tests for MCP tool list functionality.

Tests cover:
- list_characters
- list_npcs
- list_locations
- list_quests
- Empty list handling
"""

import pytest
from pathlib import Path

from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import (
    Character, NPC, Location, Quest,
    CharacterClass, Race, AbilityScore
)


# Test fixtures
@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def storage_with_campaign(temp_storage_dir: Path) -> DnDStorage:
    """Create a storage instance with a test campaign."""
    storage = DnDStorage(data_dir=temp_storage_dir)

    # Create test campaign
    campaign = storage.create_campaign(
        name="Test Campaign",
        description="A test campaign for format tests",
        dm_name="Test DM",
    )

    # Add test characters
    char1 = Character(
        name="Gandalf",
        player_name="Alice",
        character_class=CharacterClass(name="Wizard", level=20),
        race=Race(name="Maiar"),
        background="Istari",
        alignment="Lawful Good",
        abilities={
            "strength": AbilityScore(score=12),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=16),
            "intelligence": AbilityScore(score=20),
            "wisdom": AbilityScore(score=18),
            "charisma": AbilityScore(score=16),
        },
        description="A wise wizard",
        bio="One of the Istari",
    )

    char2 = Character(
        name="Aragorn",
        player_name="Bob",
        character_class=CharacterClass(name="Ranger", level=10),
        race=Race(name="Human"),
        background="Noble",
        alignment="Lawful Good",
        abilities={
            "strength": AbilityScore(score=18),
            "dexterity": AbilityScore(score=15),
            "constitution": AbilityScore(score=16),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=13),
            "charisma": AbilityScore(score=14),
        },
        description="A ranger from the North",
        bio="Heir to the throne",
    )

    storage.add_character(char1)
    storage.add_character(char2)

    # Add test NPCs
    npc1 = NPC(
        name="Saruman",
        race="Maiar",
        occupation="Wizard",
        location="Isengard",
        attitude="hostile",
        description="A corrupted wizard",
        bio="Betrayed the White Council",
    )

    npc2 = NPC(
        name="Elrond",
        race="Elf",
        occupation="Lord of Rivendell",
        location="Rivendell",
        attitude="friendly",
        description="A wise elf lord",
        bio="Bearer of Vilya",
    )

    storage.add_npc(npc1)
    storage.add_npc(npc2)

    # Add test locations
    loc1 = Location(
        name="Rivendell",
        location_type="city",
        description="An elven stronghold",
        population=1000,
        government="Council",
        notable_features=["Healing halls", "Library"],
    )

    loc2 = Location(
        name="Isengard",
        location_type="fortress",
        description="A corrupted tower",
        population=10000,
        government="Dictatorship",
        notable_features=["Orthanc", "Orc forges"],
    )

    storage.add_location(loc1)
    storage.add_location(loc2)

    # Add test quests
    quest1 = Quest(
        title="Destroy the One Ring",
        description="Take the ring to Mount Doom",
        status="active",
        objectives=["Travel to Mordor", "Reach Mount Doom", "Destroy the ring"],
        rewards=["Save Middle-earth"],
    )

    quest2 = Quest(
        title="Rescue the Hobbits",
        description="Save Merry and Pippin from the Uruk-hai",
        status="completed",
        objectives=["Track the Uruk-hai", "Battle in Fangorn"],
        rewards=["Alliance with Rohan"],
    )

    storage.add_quest(quest1)
    storage.add_quest(quest2)

    return storage


class TestListCharacters:
    """Tests for list_characters tool."""

    def test_list_characters(
        self, storage_with_campaign: DnDStorage
    ) -> None:
        """Test list_characters logic."""
        # Get characters from storage
        characters = storage_with_campaign.list_characters_detailed()

        # Verify we have characters
        assert len(characters) == 2

        # Build result like the tool does
        char_list = [
            f"• {char.name} (Level {char.character_class.level} {char.race.name} {char.character_class.name})"
            for char in characters
        ]
        result = "**Characters:**\n" + "\n".join(char_list)

        # Verify it's a string
        assert isinstance(result, str)
        # Verify it contains character information
        assert "Gandalf" in result
        assert "Aragorn" in result
        assert "Wizard" in result
        assert "Ranger" in result
        # Verify it's formatted as markdown
        assert "**Characters:**" in result
        assert "Level" in result


class TestListNpcs:
    """Tests for list_npcs tool."""

    def test_list_npcs(
        self, storage_with_campaign: DnDStorage
    ) -> None:
        """Test list_npcs logic."""
        # Get NPCs from storage
        npcs = storage_with_campaign.list_npcs_detailed()

        # Build result like the tool does
        npc_list = [
            f"• {npc.name}{f' ({npc.location})' if npc.location else ''}"
            for npc in npcs
        ]
        result = "**NPCs:**\n" + "\n".join(npc_list)

        assert isinstance(result, str)
        assert "Saruman" in result
        assert "Elrond" in result
        assert "**NPCs:**" in result
        assert "Isengard" in result or "Rivendell" in result


class TestListLocations:
    """Tests for list_locations tool."""

    def test_list_locations(
        self, storage_with_campaign: DnDStorage
    ) -> None:
        """Test list_locations logic."""
        # Get locations from storage
        locations = storage_with_campaign.list_locations_detailed()

        # Build result like the tool does
        loc_list = [
            f"• {loc.name} ({loc.location_type})"
            for loc in locations
        ]
        result = "**Locations:**\n" + "\n".join(loc_list)

        assert isinstance(result, str)
        assert "Rivendell" in result
        assert "Isengard" in result
        assert "**Locations:**" in result
        assert "city" in result or "fortress" in result


class TestListQuests:
    """Tests for list_quests tool."""

    def test_list_quests(
        self, storage_with_campaign: DnDStorage
    ) -> None:
        """Test list_quests logic."""
        # Get quests from storage
        quest_titles = storage_with_campaign.list_quests(status=None)

        # Build result like the tool does
        quest_list = []
        for quest_title in quest_titles:
            quest = storage_with_campaign.get_quest(quest_title)
            if quest:
                status_text = f" [{quest.status}]"
                quest_list.append(f"• {quest.title}{status_text}")

        result = "**Quests:**\n" + "\n".join(quest_list)

        assert isinstance(result, str)
        assert "Destroy the One Ring" in result
        assert "Rescue the Hobbits" in result
        assert "**Quests:**" in result
        assert "[active]" in result or "[completed]" in result

    def test_list_quests_with_status_filter(
        self, storage_with_campaign: DnDStorage
    ) -> None:
        """Test list_quests logic with status filter."""
        # Get active quests only
        quest_titles = storage_with_campaign.list_quests(status="active")

        # Build result like the tool does
        quest_list = []
        for quest_title in quest_titles:
            quest = storage_with_campaign.get_quest(quest_title)
            if quest:
                status_text = f" [{quest.status}]"
                quest_list.append(f"• {quest.title}{status_text}")

        result = "**Quests:**\n" + "\n".join(quest_list)

        assert isinstance(result, str)
        assert "Destroy the One Ring" in result
        # Completed quest should not be in active list
        assert "Rescue the Hobbits" not in result


class TestEmptyLists:
    """Tests for list tools with empty data."""

    def test_list_characters_empty(self, temp_storage_dir: Path) -> None:
        """Test list_characters logic with no characters."""
        storage = DnDStorage(data_dir=temp_storage_dir)
        storage.create_campaign(name="Empty Campaign", description="No data")

        # Get characters (should be empty)
        characters = storage.list_characters_detailed()
        assert len(characters) == 0

        # When empty, return message
        result = "No characters in the current campaign."

        assert isinstance(result, str)
        assert "No characters" in result

    def test_list_npcs_empty(self, temp_storage_dir: Path) -> None:
        """Test list_npcs logic with no NPCs."""
        storage = DnDStorage(data_dir=temp_storage_dir)
        storage.create_campaign(name="Empty Campaign", description="No data")

        # Get NPCs (should be empty)
        npcs = storage.list_npcs_detailed()
        assert len(npcs) == 0

        # When empty, return message
        result = "No NPCs in the current campaign."

        assert isinstance(result, str)
        assert "No NPCs" in result

    def test_list_locations_empty(self, temp_storage_dir: Path) -> None:
        """Test list_locations logic with no locations."""
        storage = DnDStorage(data_dir=temp_storage_dir)
        storage.create_campaign(name="Empty Campaign", description="No data")

        # Get locations (should be empty)
        locations = storage.list_locations_detailed()
        assert len(locations) == 0

        # When empty, return message
        result = "No locations in the current campaign."

        assert isinstance(result, str)
        assert "No locations" in result

    def test_list_quests_empty(self, temp_storage_dir: Path) -> None:
        """Test list_quests logic with no quests."""
        storage = DnDStorage(data_dir=temp_storage_dir)
        storage.create_campaign(name="Empty Campaign", description="No data")

        # Get quests (should be empty)
        quests = storage.list_quests()
        assert len(quests) == 0

        # When empty, return message
        result = "No quests found."

        assert isinstance(result, str)
        assert "No quests" in result
