"""
Test file for legacy campaign detection and backward compatibility.

Tests the automatic detection of campaign storage format (monolithic vs split)
and ensures existing monolithic campaigns continue to work without changes.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime

# Direct module imports (bypassing package __init__ which imports main)
import gamemaster_mcp.storage as storage_module
import gamemaster_mcp.models as models_module

DnDStorage = storage_module.DnDStorage
StorageFormat = storage_module.StorageFormat
Campaign = models_module.Campaign
GameState = models_module.GameState
Character = models_module.Character
CharacterClass = models_module.CharacterClass
Race = models_module.Race


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage instance for testing."""
    return DnDStorage(tmp_path / "test_data")


@pytest.fixture
def monolithic_campaign(tmp_path):
    """Create a monolithic campaign file for testing."""
    storage_path = tmp_path / "test_data"
    campaigns_dir = storage_path / "campaigns"
    campaigns_dir.mkdir(parents=True)

    # Create a sample monolithic campaign JSON file
    campaign_data = {
        "name": "Test Monolithic Campaign",
        "description": "A test campaign in monolithic format",
        "dm_name": "Test DM",
        "setting": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "characters": {},
        "npcs": {},
        "locations": {},
        "quests": {},
        "sessions": [],
        "game_state": {
            "campaign_name": "Test Monolithic Campaign",
            "current_session": 1,
            "session_date": None,
            "location": None,
            "active_quests": [],
            "party_level": 1,
            "notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    }

    campaign_file = campaigns_dir / "Test Monolithic Campaign.json"
    with open(campaign_file, 'w', encoding='utf-8') as f:
        json.dump(campaign_data, f)

    return storage_path


@pytest.fixture
def split_campaign(tmp_path):
    """Create a split campaign directory for testing."""
    storage_path = tmp_path / "test_data"
    campaigns_dir = storage_path / "campaigns"
    campaign_dir = campaigns_dir / "Test Split Campaign"
    campaign_dir.mkdir(parents=True)

    # Create metadata.json
    metadata = {
        "name": "Test Split Campaign",
        "description": "A test campaign in split format",
        "dm_name": "Test DM",
        "setting": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    with open(campaign_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f)

    # Create empty characters directory
    (campaign_dir / "characters").mkdir()

    return storage_path


class TestFormatDetection:
    """Test campaign format detection logic."""

    def test_detect_monolithic_format(self, monolithic_campaign):
        """Test detection of monolithic campaign format."""
        storage = DnDStorage(monolithic_campaign)
        format_detected = storage._detect_campaign_format("Test Monolithic Campaign")
        assert format_detected == StorageFormat.MONOLITHIC

    def test_detect_split_format(self, split_campaign):
        """Test detection of split campaign format."""
        storage = DnDStorage(split_campaign)
        format_detected = storage._detect_campaign_format("Test Split Campaign")
        assert format_detected == StorageFormat.SPLIT

    def test_detect_not_found(self, temp_storage):
        """Test detection when campaign doesn't exist."""
        format_detected = temp_storage._detect_campaign_format("Nonexistent Campaign")
        assert format_detected == StorageFormat.NOT_FOUND

    def test_detect_directory_without_metadata(self, tmp_path):
        """Test detection of directory without metadata.json."""
        storage_path = tmp_path / "test_data"
        campaigns_dir = storage_path / "campaigns"
        campaign_dir = campaigns_dir / "Invalid Campaign"
        campaign_dir.mkdir(parents=True)

        storage = DnDStorage(storage_path)
        format_detected = storage._detect_campaign_format("Invalid Campaign")
        # Should be NOT_FOUND because metadata.json is missing
        assert format_detected == StorageFormat.NOT_FOUND


class TestMonolithicBackwardCompatibility:
    """Test backward compatibility with existing monolithic campaigns."""

    def test_load_monolithic_campaign(self, monolithic_campaign):
        """Test loading an existing monolithic campaign."""
        storage = DnDStorage(monolithic_campaign)
        campaign = storage.load_campaign("Test Monolithic Campaign")

        assert campaign is not None
        assert campaign.name == "Test Monolithic Campaign"
        assert campaign.description == "A test campaign in monolithic format"
        assert storage._current_format == StorageFormat.MONOLITHIC

    def test_save_monolithic_campaign(self, monolithic_campaign):
        """Test that saving preserves monolithic format."""
        storage = DnDStorage(monolithic_campaign)
        storage.load_campaign("Test Monolithic Campaign")

        # Modify campaign
        storage.update_campaign(description="Updated description")

        # Verify file still exists and was updated
        campaign_file = monolithic_campaign / "campaigns" / "Test Monolithic Campaign.json"
        assert campaign_file.exists()

        with open(campaign_file, 'r') as f:
            data = json.load(f)
        assert data["description"] == "Updated description"

    def test_list_campaigns_includes_monolithic(self, monolithic_campaign):
        """Test that list_campaigns includes monolithic campaigns."""
        storage = DnDStorage(monolithic_campaign)
        campaigns = storage.list_campaigns()

        assert "Test Monolithic Campaign" in campaigns

    def test_character_operations_on_monolithic(self, monolithic_campaign):
        """Test character operations work on monolithic campaigns."""
        storage = DnDStorage(monolithic_campaign)
        storage.load_campaign("Test Monolithic Campaign")

        # Add a character
        character = Character(
            name="Test Hero",
            character_class=CharacterClass(name="Fighter", level=1),
            race=Race(name="Human"),
        )
        storage.add_character(character)

        # Verify character was added
        retrieved = storage.get_character("Test Hero")
        assert retrieved is not None
        assert retrieved.name == "Test Hero"

        # Verify file was updated
        campaign_file = monolithic_campaign / "campaigns" / "Test Monolithic Campaign.json"
        with open(campaign_file, 'r') as f:
            data = json.load(f)
        assert "Test Hero" in data["characters"]


class TestMixedCampaigns:
    """Test handling of mixed monolithic and split campaigns."""

    def test_list_both_formats(self, tmp_path):
        """Test listing campaigns when both formats exist."""
        storage_path = tmp_path / "test_data"
        campaigns_dir = storage_path / "campaigns"
        campaigns_dir.mkdir(parents=True)

        # Create monolithic campaign
        mono_data = {
            "name": "Mono Campaign",
            "description": "Monolithic",
            "dm_name": None,
            "setting": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "sessions": [],
            "game_state": {
                "campaign_name": "Mono Campaign",
                "current_session": 1,
                "session_date": None,
                "location": None,
                "active_quests": [],
                "party_level": 1,
                "notes": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        }
        with open(campaigns_dir / "Mono Campaign.json", 'w') as f:
            json.dump(mono_data, f)

        # Create split campaign
        split_dir = campaigns_dir / "Split Campaign"
        split_dir.mkdir()
        metadata = {
            "name": "Split Campaign",
            "description": "Split",
            "dm_name": None,
            "setting": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        with open(split_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)

        storage = DnDStorage(storage_path)
        campaigns = storage.list_campaigns()

        assert "Mono Campaign" in campaigns
        assert "Split Campaign" in campaigns
        assert len(campaigns) == 2


class TestNewCampaignFormat:
    """Test that new campaigns use the correct format."""

    def test_new_campaign_format(self, temp_storage):
        """Test that newly created campaigns use the intended format."""
        campaign = temp_storage.create_campaign(
            name="New Campaign",
            description="A new test campaign",
            dm_name="Test DM"
        )

        assert campaign is not None
        assert campaign.name == "New Campaign"
        # Currently defaults to monolithic until Task #2 is complete
        assert temp_storage._current_format == StorageFormat.MONOLITHIC


class TestSplitFormatPlaceholder:
    """Test that split format operations raise NotImplementedError."""

    def test_load_split_raises_not_implemented(self, split_campaign):
        """Test that loading split campaigns raises NotImplementedError."""
        storage = DnDStorage(split_campaign)

        with pytest.raises(NotImplementedError) as exc_info:
            storage.load_campaign("Test Split Campaign")

        assert "Task #2" in str(exc_info.value)
        assert "SplitStorageBackend" in str(exc_info.value)


class TestCharacterIndexing:
    """Test that character indexing works with format detection."""

    def test_index_rebuilt_on_load(self, monolithic_campaign):
        """Test that character indexes are rebuilt when loading campaigns."""
        # First, add a character to the campaign file
        campaign_file = monolithic_campaign / "campaigns" / "Test Monolithic Campaign.json"
        with open(campaign_file, 'r') as f:
            data = json.load(f)

        # Add a character directly to the JSON
        char_data = {
            "id": "test123",
            "name": "Test Character",
            "character_class": {"name": "Fighter", "level": 1, "subclass": None, "hit_dice": "1d10"},
            "race": {"name": "Human", "subrace": None},
            "player_name": "TestPlayer",
            "background": None,
            "alignment": None,
            "experience_points": 0,
            "abilities": {},
            "skills": {},
            "saving_throws": {},
            "armor_class": 10,
            "initiative": 0,
            "speed": 30,
            "hit_points": {"current": 10, "maximum": 10, "temporary": 0},
            "hit_dice_remaining": "1d10",
            "death_saves": {"successes": 0, "failures": 0},
            "inventory": [],
            "spells": [],
            "features": [],
            "notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        data["characters"]["Test Character"] = char_data

        with open(campaign_file, 'w') as f:
            json.dump(data, f)

        # Now load and verify indexes
        storage = DnDStorage(monolithic_campaign)
        storage.load_campaign("Test Monolithic Campaign")

        # Test lookup by ID
        char_by_id = storage.get_character("test123")
        assert char_by_id is not None
        assert char_by_id.name == "Test Character"

        # Test lookup by player name
        char_by_player = storage.get_character("TestPlayer")
        assert char_by_player is not None
        assert char_by_player.name == "Test Character"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
