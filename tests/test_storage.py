"""
Unit tests for DnDStorage format detection and backward compatibility.

Tests cover:
- Campaign format detection (monolithic vs split)
- Loading legacy monolithic campaigns
- Backward compatibility with existing campaigns
- Integration between storage formats
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

from gamemaster_mcp.storage import DnDStorage, StorageFormat, new_uuid
from gamemaster_mcp.models import (
    Campaign, Character, GameState, CharacterClass, Race, AbilityScore
)


# Test fixtures
@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def sample_character() -> Character:
    """Create a sample character for testing."""
    return Character(
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
        bio="Heir to the throne of Gondor",
    )


class TestFormatDetection:
    """Tests for detecting campaign storage format."""

    def test_detect_monolithic_format(self, temp_storage_dir: Path) -> None:
        """Test detection of monolithic format campaigns."""
        # Create a monolithic campaign file
        campaigns_dir = temp_storage_dir / "campaigns"
        campaigns_dir.mkdir(parents=True)

        campaign_file = campaigns_dir / "Test Campaign.json"
        campaign_data = {
            "id": new_uuid(),
            "name": "Test Campaign",
            "description": "A test campaign",
            "dm_name": "Test DM",
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {
                "campaign_name": "Test Campaign",
                "current_session": 1,
                "current_location": None,
                "current_date_in_game": None,
                "party_level": 1,
                "party_funds": "0 gp",
                "in_combat": False,
                "initiative_order": [],
                "current_turn": None,
                "notes": "",
                "active_quests": [],
                "updated_at": datetime.now().isoformat(),
            },
        }

        with open(campaign_file, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f)

        # Create storage and detect format
        storage = DnDStorage(data_dir=temp_storage_dir)
        detected_format = storage._detect_campaign_format("Test Campaign")

        assert detected_format == StorageFormat.MONOLITHIC

    def test_detect_split_format(self, temp_storage_dir: Path) -> None:
        """Test detection of split format campaigns."""
        # Create a split campaign directory structure
        campaigns_dir = temp_storage_dir / "campaigns"
        campaign_dir = campaigns_dir / "Test Split Campaign"
        campaign_dir.mkdir(parents=True)

        # Create campaign.json (metadata only)
        metadata = {
            "id": new_uuid(),
            "name": "Test Split Campaign",
            "description": "A split format campaign",
            "dm_name": "Test DM",
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
        }

        with open(campaign_dir / "campaign.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        # Create storage and detect format
        storage = DnDStorage(data_dir=temp_storage_dir)
        detected_format = storage._detect_campaign_format("Test Split Campaign")

        assert detected_format == StorageFormat.SPLIT

    def test_detect_nonexistent_campaign(self, temp_storage_dir: Path) -> None:
        """Test detection of non-existent campaigns."""
        storage = DnDStorage(data_dir=temp_storage_dir)
        detected_format = storage._detect_campaign_format("Nonexistent Campaign")

        assert detected_format == StorageFormat.NOT_FOUND

    def test_detect_invalid_split_campaign_missing_metadata(
        self, temp_storage_dir: Path
    ) -> None:
        """Test detection of invalid split campaign (directory exists but no campaign.json)."""
        # Create directory without campaign.json
        campaigns_dir = temp_storage_dir / "campaigns"
        campaign_dir = campaigns_dir / "Invalid Campaign"
        campaign_dir.mkdir(parents=True)

        storage = DnDStorage(data_dir=temp_storage_dir)
        detected_format = storage._detect_campaign_format("Invalid Campaign")

        # Should not detect as valid split format
        assert detected_format != StorageFormat.SPLIT


class TestLoadLegacyMonolithic:
    """Tests for loading legacy monolithic format campaigns."""

    def test_load_legacy_monolithic_campaign(
        self, temp_storage_dir: Path, sample_character: Character
    ) -> None:
        """Test loading a campaign in monolithic format."""
        # Create a monolithic campaign file
        campaigns_dir = temp_storage_dir / "campaigns"
        campaigns_dir.mkdir(parents=True)

        campaign_file = campaigns_dir / "Legacy Campaign.json"
        campaign_data = {
            "id": new_uuid(),
            "name": "Legacy Campaign",
            "description": "A legacy monolithic campaign",
            "dm_name": "Legacy DM",
            "setting": "Forgotten Realms",
            "world_notes": "A classic D&D setting",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "characters": {
                "Aragorn": sample_character.model_dump(mode='json')
            },
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {
                "campaign_name": "Legacy Campaign",
                "current_session": 1,
                "current_location": "Rivendell",
                "current_date_in_game": None,
                "party_level": 10,
                "party_funds": "1000 gp",
                "in_combat": False,
                "initiative_order": [],
                "current_turn": None,
                "notes": "The fellowship has formed",
                "active_quests": [],
                "updated_at": datetime.now().isoformat(),
            },
        }

        with open(campaign_file, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f)

        # Load campaign using DnDStorage
        storage = DnDStorage(data_dir=temp_storage_dir)
        campaign = storage.load_campaign("Legacy Campaign")

        # Verify campaign was loaded correctly
        assert campaign.name == "Legacy Campaign"
        assert campaign.description == "A legacy monolithic campaign"
        assert campaign.dm_name == "Legacy DM"
        assert "Aragorn" in campaign.characters
        assert campaign.characters["Aragorn"].name == "Aragorn"
        assert campaign.characters["Aragorn"].player_name == "Bob"
        assert campaign.game_state.current_location == "Rivendell"
        assert campaign.game_state.party_level == 10

    def test_load_monolithic_then_save_as_split(
        self, temp_storage_dir: Path, sample_character: Character
    ) -> None:
        """Test loading a monolithic campaign and saving it (should remain monolithic)."""
        # Create a monolithic campaign
        campaigns_dir = temp_storage_dir / "campaigns"
        campaigns_dir.mkdir(parents=True)

        campaign_file = campaigns_dir / "Conversion Test.json"
        campaign_data = {
            "id": new_uuid(),
            "name": "Conversion Test",
            "description": "Testing format preservation",
            "dm_name": "Test DM",
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {
                "campaign_name": "Conversion Test",
                "current_session": 1,
                "current_location": None,
                "current_date_in_game": None,
                "party_level": 1,
                "party_funds": "0 gp",
                "in_combat": False,
                "initiative_order": [],
                "current_turn": None,
                "notes": "",
                "active_quests": [],
                "updated_at": datetime.now().isoformat(),
            },
        }

        with open(campaign_file, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f)

        # Load and modify campaign
        storage = DnDStorage(data_dir=temp_storage_dir)
        campaign = storage.load_campaign("Conversion Test")
        storage.add_character(sample_character)

        # Verify file was updated (monolithic format preserved)
        assert campaign_file.exists()
        with open(campaign_file, "r", encoding="utf-8") as f:
            updated_data = json.load(f)

        assert "Aragorn" in updated_data["characters"]


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing campaign structures."""

    def test_list_campaigns_includes_both_formats(
        self, temp_storage_dir: Path
    ) -> None:
        """Test that list_campaigns returns both monolithic and split campaigns."""
        campaigns_dir = temp_storage_dir / "campaigns"
        campaigns_dir.mkdir(parents=True)

        # Create monolithic campaign
        monolithic_file = campaigns_dir / "Monolithic Campaign.json"
        monolithic_data = {
            "id": new_uuid(),
            "name": "Monolithic Campaign",
            "description": "A monolithic campaign",
            "dm_name": None,
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {
                "campaign_name": "Monolithic Campaign",
                "current_session": 1,
                "current_location": None,
                "current_date_in_game": None,
                "party_level": 1,
                "party_funds": "0 gp",
                "in_combat": False,
                "initiative_order": [],
                "current_turn": None,
                "notes": "",
                "active_quests": [],
                "updated_at": datetime.now().isoformat(),
            },
        }

        with open(monolithic_file, "w", encoding="utf-8") as f:
            json.dump(monolithic_data, f)

        # Create split campaign
        split_dir = campaigns_dir / "Split Campaign"
        split_dir.mkdir()
        split_metadata = {
            "id": new_uuid(),
            "name": "Split Campaign",
            "description": "A split campaign",
            "dm_name": None,
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
        }

        with open(split_dir / "campaign.json", "w", encoding="utf-8") as f:
            json.dump(split_metadata, f)

        # List campaigns
        storage = DnDStorage(data_dir=temp_storage_dir)
        campaigns = storage.list_campaigns()

        # Both should be listed
        assert "Monolithic Campaign" in campaigns
        assert "Split Campaign" in campaigns
        assert len(campaigns) == 2

    def test_new_campaigns_use_split_format(self, temp_storage_dir: Path) -> None:
        """Test that newly created campaigns use split format by default."""
        storage = DnDStorage(data_dir=temp_storage_dir)

        # Create new campaign
        campaign = storage.create_campaign(
            name="New Campaign",
            description="A newly created campaign",
            dm_name="New DM",
        )

        # Verify split format was used
        campaign_dir = temp_storage_dir / "campaigns" / "New Campaign"
        assert campaign_dir.exists()
        assert campaign_dir.is_dir()
        assert (campaign_dir / "campaign.json").exists()

        # Verify format detection
        detected_format = storage._detect_campaign_format("New Campaign")
        assert detected_format == StorageFormat.SPLIT

    def test_load_most_recent_campaign_any_format(
        self, temp_storage_dir: Path
    ) -> None:
        """Test that _load_current_campaign works with both formats."""
        campaigns_dir = temp_storage_dir / "campaigns"
        campaigns_dir.mkdir(parents=True)

        # Create older monolithic campaign
        monolithic_file = campaigns_dir / "Old Campaign.json"
        old_data = {
            "id": new_uuid(),
            "name": "Old Campaign",
            "description": "An older campaign",
            "dm_name": None,
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {
                "campaign_name": "Old Campaign",
                "current_session": 1,
                "current_location": None,
                "current_date_in_game": None,
                "party_level": 1,
                "party_funds": "0 gp",
                "in_combat": False,
                "initiative_order": [],
                "current_turn": None,
                "notes": "",
                "active_quests": [],
                "updated_at": datetime.now().isoformat(),
            },
        }

        with open(monolithic_file, "w", encoding="utf-8") as f:
            json.dump(old_data, f)

        # Wait a bit and create newer split campaign
        import time
        time.sleep(0.01)

        split_dir = campaigns_dir / "Recent Campaign"
        split_dir.mkdir()
        recent_metadata = {
            "id": new_uuid(),
            "name": "Recent Campaign",
            "description": "A more recent campaign",
            "dm_name": None,
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
        }

        with open(split_dir / "campaign.json", "w", encoding="utf-8") as f:
            json.dump(recent_metadata, f)

        # Initialize storage (should load most recent)
        storage = DnDStorage(data_dir=temp_storage_dir)
        current_campaign = storage.get_current_campaign()

        # Should load the more recent split campaign
        assert current_campaign is not None
        assert current_campaign.name == "Recent Campaign"
