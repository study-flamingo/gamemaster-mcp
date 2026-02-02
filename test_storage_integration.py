"""
Integration tests for DnDStorage with split storage backend.
Tests that new campaigns use split format and existing campaigns work correctly.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from gamemaster_mcp.storage import DnDStorage, StorageFormat
from gamemaster_mcp.models import (
    Character, CharacterClass, Race, AbilityScore,
    NPC, Location, Quest
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir):
    """Create a DnDStorage instance with temp directory."""
    return DnDStorage(data_dir=temp_storage_dir)


@pytest.fixture
def sample_character():
    """Create a sample character for testing."""
    return Character(
        name="Gandalf",
        player_name="John",
        character_class=CharacterClass(name="Wizard", level=10, hit_dice="1d6"),
        race=Race(name="Human"),
        abilities={
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=12),
            "constitution": AbilityScore(score=14),
            "intelligence": AbilityScore(score=20),
            "wisdom": AbilityScore(score=16),
            "charisma": AbilityScore(score=15),
        }
    )


class TestSplitStorageIntegration:
    """Tests for split storage integration with DnDStorage."""

    def test_new_campaign_uses_split_format(self, storage):
        """Test that new campaigns use split storage format."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="A test campaign"
        )

        # Should use split format
        assert storage._current_format == StorageFormat.SPLIT

        # Verify directory structure exists
        campaign_dir = storage.data_dir / "campaigns" / "Test Campaign"
        assert campaign_dir.exists()
        assert (campaign_dir / "campaign.json").exists()
        assert (campaign_dir / "characters.json").exists()
        assert (campaign_dir / "sessions").exists()

    def test_add_character_to_split_campaign(self, storage, sample_character):
        """Test adding a character to a split storage campaign."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        # Add character
        storage.add_character(sample_character)

        # Verify character saved to split storage
        campaign_dir = storage.data_dir / "campaigns" / "Test Campaign"
        char_file = campaign_dir / "characters.json"
        assert char_file.exists()

        import json
        with open(char_file, 'r') as f:
            data = json.load(f)
        assert "Gandalf" in data

    def test_update_character_in_split_campaign(self, storage, sample_character):
        """Test updating a character in split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        storage.add_character(sample_character)

        # Update character
        storage.update_character("Gandalf", level=15)

        # Verify update persisted
        char = storage.get_character("Gandalf")
        assert char.character_class.level == 15

    def test_remove_character_from_split_campaign(self, storage, sample_character):
        """Test removing a character from split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        storage.add_character(sample_character)

        # Remove character
        storage.remove_character("Gandalf")

        # Verify removal
        assert storage.get_character("Gandalf") is None

    def test_batch_update_with_split_storage(self, storage, sample_character):
        """Test batch updates work with split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        # Batch update
        with storage.batch_update():
            storage.add_character(sample_character)
            char2 = Character(
                name="Aragorn",
                character_class=CharacterClass(name="Ranger", level=8, hit_dice="1d10"),
                race=Race(name="Human")
            )
            storage.add_character(char2)

        # Verify both characters saved
        assert storage.get_character("Gandalf") is not None
        assert storage.get_character("Aragorn") is not None

    def test_character_index_rebuilding_with_split_storage(self, storage, sample_character):
        """Test that character indexes work with split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        storage.add_character(sample_character)

        # Reload campaign to test index rebuilding
        new_storage = DnDStorage(data_dir=storage.data_dir)
        new_storage.load_campaign("Test Campaign")

        # Test lookup by ID
        char = new_storage.get_character(sample_character.id)
        assert char is not None
        assert char.name == "Gandalf"

        # Test lookup by player name
        char = new_storage.get_character("John")
        assert char is not None
        assert char.name == "Gandalf"

    def test_load_split_campaign(self, storage, sample_character):
        """Test loading a split storage campaign."""
        # Create and save campaign
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="A test campaign"
        )
        storage.add_character(sample_character)

        # Create new storage instance and load
        new_storage = DnDStorage(data_dir=storage.data_dir)
        loaded_campaign = new_storage.load_campaign("Test Campaign")

        assert loaded_campaign.name == "Test Campaign"
        assert new_storage._current_format == StorageFormat.SPLIT
        assert len(loaded_campaign.characters) == 1
        assert "Gandalf" in loaded_campaign.characters

    def test_split_storage_with_npcs(self, storage):
        """Test NPC management with split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        npc = NPC(
            name="Shopkeeper Bob",
            description="A friendly merchant",
            race="Dwarf",
            occupation="Merchant"
        )
        storage.add_npc(npc)

        # Verify NPC saved
        campaign_dir = storage.data_dir / "campaigns" / "Test Campaign"
        npc_file = campaign_dir / "npcs.json"
        assert npc_file.exists()

    def test_split_storage_with_locations(self, storage):
        """Test location management with split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        location = Location(
            name="Rivendell",
            location_type="city",
            description="An elven city"
        )
        storage.add_location(location)

        # Verify location saved
        campaign_dir = storage.data_dir / "campaigns" / "Test Campaign"
        loc_file = campaign_dir / "locations.json"
        assert loc_file.exists()

    def test_split_storage_with_quests(self, storage):
        """Test quest management with split storage."""
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        quest = Quest(
            title="Save the World",
            description="A critical quest",
            status="active"
        )
        storage.add_quest(quest)

        # Verify quest saved
        campaign_dir = storage.data_dir / "campaigns" / "Test Campaign"
        quest_file = campaign_dir / "quests.json"
        assert quest_file.exists()

    def test_list_campaigns_includes_split_campaigns(self, storage):
        """Test that list_campaigns includes split format campaigns."""
        storage.create_campaign(
            name="Split Campaign 1",
            description="First split campaign"
        )
        storage.create_campaign(
            name="Split Campaign 2",
            description="Second split campaign"
        )

        campaigns = storage.list_campaigns()
        assert "Split Campaign 1" in campaigns
        assert "Split Campaign 2" in campaigns

    def test_load_most_recent_split_campaign(self, storage):
        """Test that the most recent split campaign is loaded on init."""
        import time

        # Create first campaign
        storage.create_campaign(
            name="Old Campaign",
            description="Old"
        )
        time.sleep(0.01)

        # Create second campaign
        storage.create_campaign(
            name="New Campaign",
            description="New"
        )

        # Create new storage instance
        new_storage = DnDStorage(data_dir=storage.data_dir)

        # Should load the most recent campaign
        assert new_storage._current_campaign is not None
        assert new_storage._current_campaign.name == "New Campaign"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
