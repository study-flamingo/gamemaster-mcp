"""
Unit tests for SplitStorageBackend class.
Tests per-file save/load, dirty tracking, and atomic writes.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from gamemaster_mcp.storage import SplitStorageBackend
from gamemaster_mcp.models import (
    Campaign, Character, CharacterClass, Race, AbilityScore,
    NPC, Location, Quest, CombatEncounter, SessionNote, GameState
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def split_storage(temp_storage_dir):
    """Create a SplitStorageBackend instance with temp directory."""
    return SplitStorageBackend(data_dir=temp_storage_dir)


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


@pytest.fixture
def sample_npc():
    """Create a sample NPC for testing."""
    return NPC(
        name="Shopkeeper Bob",
        description="A friendly dwarf merchant",
        race="Dwarf",
        occupation="Merchant",
        location="Market Square",
        attitude="friendly"
    )


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        name="Rivendell",
        location_type="city",
        description="The last homely house east of the sea",
        population=5000,
        government="Council of Elrond",
        notable_features=["Healing springs", "Great library"]
    )


@pytest.fixture
def sample_quest():
    """Create a sample quest for testing."""
    return Quest(
        title="Destroy the One Ring",
        description="Take the ring to Mount Doom and destroy it",
        giver="Gandalf",
        status="active",
        objectives=["Reach Mordor", "Climb Mount Doom", "Destroy the ring"],
        reward="Save Middle Earth"
    )


@pytest.fixture
def sample_encounter():
    """Create a sample encounter for testing."""
    return CombatEncounter(
        name="Orc Ambush",
        description="A group of orcs attacks the party",
        enemies=["Orc Warrior x5", "Orc Archer x2"],
        difficulty="medium",
        experience_value=1000,
        location="Forest Path"
    )


@pytest.fixture
def sample_session():
    """Create a sample session note for testing."""
    return SessionNote(
        session_number=1,
        title="The Adventure Begins",
        summary="The party meets in a tavern and accepts their first quest",
        events=["Met at tavern", "Accepted quest", "Traveled to forest"],
        characters_present=["Gandalf", "Aragorn", "Legolas"],
        experience_gained=500
    )


class TestSplitStorageBackendInit:
    """Tests for SplitStorageBackend initialization."""

    def test_init_creates_directory_structure(self, temp_storage_dir):
        """Test that initialization creates the expected directory structure."""
        storage = SplitStorageBackend(data_dir=temp_storage_dir)

        assert storage.data_dir.exists()
        assert (storage.data_dir / "campaigns").exists()
        assert storage._current_campaign is None
        assert len(storage._section_hashes) == 7

    def test_init_with_nonexistent_dir(self, temp_storage_dir):
        """Test initialization with a non-existent directory."""
        new_dir = temp_storage_dir / "new_data"
        storage = SplitStorageBackend(data_dir=new_dir)

        assert new_dir.exists()
        assert (new_dir / "campaigns").exists()


class TestCampaignDirectoryStructure:
    """Tests for campaign directory structure creation."""

    def test_ensure_campaign_structure(self, split_storage):
        """Test that campaign directory structure is created correctly."""
        campaign_name = "Test Campaign"
        split_storage._ensure_campaign_structure(campaign_name)

        campaign_dir = split_storage._get_campaign_dir(campaign_name)
        assert campaign_dir.exists()
        assert (campaign_dir / "sessions").exists()

    def test_get_campaign_dir_with_special_chars(self, split_storage):
        """Test that campaign names with special characters are sanitized."""
        campaign_name = "Test: Campaign / With \\ Special * Chars"
        campaign_dir = split_storage._get_campaign_dir(campaign_name)

        # Should only contain alphanumeric and allowed special chars
        assert all(c.isalnum() or c in (' ', '-', '_', "'") for c in campaign_dir.name)

    def test_get_campaign_dir_uses_current_campaign(self, split_storage, sample_character):
        """Test that _get_campaign_dir uses current campaign when name is None."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="A test campaign"
        )

        # Should not raise error when campaign_name is None
        campaign_dir = split_storage._get_campaign_dir()
        assert campaign_dir.name == "Test Campaign"

    def test_get_campaign_dir_raises_without_name_or_current(self, split_storage):
        """Test that _get_campaign_dir raises error without name or current campaign."""
        with pytest.raises(ValueError, match="No campaign name provided"):
            split_storage._get_campaign_dir()


class TestCampaignCreation:
    """Tests for campaign creation."""

    def test_create_campaign_basic(self, split_storage):
        """Test basic campaign creation."""
        campaign = split_storage.create_campaign(
            name="Middle Earth",
            description="A campaign in Tolkien's world"
        )

        assert campaign.name == "Middle Earth"
        assert campaign.description == "A campaign in Tolkien's world"
        assert split_storage._current_campaign == campaign

        # Check directory structure created
        campaign_dir = split_storage._get_campaign_dir()
        assert campaign_dir.exists()
        assert (campaign_dir / "sessions").exists()
        assert (campaign_dir / "campaign.json").exists()

    def test_create_campaign_with_dm_and_setting(self, split_storage):
        """Test campaign creation with DM name and setting."""
        campaign = split_storage.create_campaign(
            name="Dark Sun",
            description="A harsh desert world",
            dm_name="DM Dave",
            setting="Athas"
        )

        assert campaign.dm_name == "DM Dave"
        assert campaign.setting == "Athas"

    def test_create_campaign_saves_all_files(self, split_storage):
        """Test that creating a campaign saves all expected files."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        campaign_dir = split_storage._get_campaign_dir()

        # Check all expected files exist (even if empty)
        assert (campaign_dir / "campaign.json").exists()
        assert (campaign_dir / "characters.json").exists()
        assert (campaign_dir / "npcs.json").exists()
        assert (campaign_dir / "locations.json").exists()
        assert (campaign_dir / "quests.json").exists()
        assert (campaign_dir / "encounters.json").exists()
        assert (campaign_dir / "game_state.json").exists()


class TestAtomicWrites:
    """Tests for atomic write functionality."""

    def test_atomic_write_success(self, split_storage):
        """Test successful atomic write."""
        test_file = split_storage.data_dir / "test.json"
        test_data = {"key": "value", "number": 42}

        split_storage._atomic_write(test_file, test_data)

        assert test_file.exists()
        with open(test_file, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_atomic_write_removes_temp_on_error(self, split_storage, monkeypatch):
        """Test that temp file is removed if write fails."""
        test_file = split_storage.data_dir / "test.json"

        # Simulate write error by making json.dump raise an exception
        def mock_dump(*args, **kwargs):
            raise RuntimeError("Simulated write error")

        monkeypatch.setattr("json.dump", mock_dump)

        with pytest.raises(RuntimeError):
            split_storage._atomic_write(test_file, {"key": "value"})

        # Temp file should be cleaned up
        temp_file = test_file.with_suffix('.tmp')
        assert not temp_file.exists()


class TestDirtyTracking:
    """Tests for per-section dirty tracking."""

    def test_compute_section_hash(self, split_storage):
        """Test hash computation for data sections."""
        data1 = {"name": "Test", "value": 123}
        data2 = {"name": "Test", "value": 123}
        data3 = {"name": "Test", "value": 456}

        hash1 = split_storage._compute_section_hash(data1)
        hash2 = split_storage._compute_section_hash(data2)
        hash3 = split_storage._compute_section_hash(data3)

        assert hash1 == hash2  # Same data should have same hash
        assert hash1 != hash3  # Different data should have different hash

    def test_save_skips_unchanged_characters(self, split_storage, sample_character):
        """Test that saving unchanged characters is skipped."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        # Add character and save
        campaign.characters[sample_character.name] = sample_character
        split_storage._save_characters(force=True)

        # Get modification time
        char_file = split_storage._get_campaign_dir() / "characters.json"
        mtime_before = char_file.stat().st_mtime

        # Save again without changes - should skip
        split_storage._save_characters(force=False)
        mtime_after = char_file.stat().st_mtime

        # File should not have been modified
        assert mtime_before == mtime_after

    def test_force_save_overwrites_unchanged(self, split_storage, sample_character):
        """Test that force=True saves even when data is unchanged."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        campaign.characters[sample_character.name] = sample_character
        split_storage._save_characters(force=True)

        char_file = split_storage._get_campaign_dir() / "characters.json"
        mtime_before = char_file.stat().st_mtime

        # Wait a bit to ensure timestamp would change
        import time
        time.sleep(0.01)

        # Force save - should write even though unchanged
        split_storage._save_characters(force=True)
        mtime_after = char_file.stat().st_mtime

        # With force=True, file should have been rewritten
        assert mtime_after >= mtime_before


class TestSaveCharacters:
    """Tests for character saving."""

    def test_save_characters_empty(self, split_storage):
        """Test saving empty characters dict."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        split_storage._save_characters(force=True)

        char_file = split_storage._get_campaign_dir() / "characters.json"
        assert char_file.exists()

        with open(char_file, 'r') as f:
            data = json.load(f)
        assert data == {}

    def test_save_characters_single(self, split_storage, sample_character):
        """Test saving a single character."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.characters[sample_character.name] = sample_character

        split_storage._save_characters(force=True)

        char_file = split_storage._get_campaign_dir() / "characters.json"
        with open(char_file, 'r') as f:
            data = json.load(f)

        assert "Gandalf" in data
        assert data["Gandalf"]["name"] == "Gandalf"
        assert data["Gandalf"]["player_name"] == "John"

    def test_save_characters_multiple(self, split_storage, sample_character):
        """Test saving multiple characters."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        char2 = Character(
            name="Aragorn",
            player_name="Mike",
            character_class=CharacterClass(name="Ranger", level=8, hit_dice="1d10"),
            race=Race(name="Human")
        )

        campaign.characters[sample_character.name] = sample_character
        campaign.characters[char2.name] = char2

        split_storage._save_characters(force=True)

        char_file = split_storage._get_campaign_dir() / "characters.json"
        with open(char_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 2
        assert "Gandalf" in data
        assert "Aragorn" in data


class TestSaveNPCs:
    """Tests for NPC saving."""

    def test_save_npcs_single(self, split_storage, sample_npc):
        """Test saving a single NPC."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.npcs[sample_npc.name] = sample_npc

        split_storage._save_npcs(force=True)

        npc_file = split_storage._get_campaign_dir() / "npcs.json"
        with open(npc_file, 'r') as f:
            data = json.load(f)

        assert "Shopkeeper Bob" in data
        assert data["Shopkeeper Bob"]["race"] == "Dwarf"
        assert data["Shopkeeper Bob"]["occupation"] == "Merchant"


class TestSaveLocations:
    """Tests for location saving."""

    def test_save_locations_single(self, split_storage, sample_location):
        """Test saving a single location."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.locations[sample_location.name] = sample_location

        split_storage._save_locations(force=True)

        loc_file = split_storage._get_campaign_dir() / "locations.json"
        with open(loc_file, 'r') as f:
            data = json.load(f)

        assert "Rivendell" in data
        assert data["Rivendell"]["location_type"] == "city"
        assert data["Rivendell"]["population"] == 5000


class TestSaveQuests:
    """Tests for quest saving."""

    def test_save_quests_single(self, split_storage, sample_quest):
        """Test saving a single quest."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.quests[sample_quest.title] = sample_quest

        split_storage._save_quests(force=True)

        quest_file = split_storage._get_campaign_dir() / "quests.json"
        with open(quest_file, 'r') as f:
            data = json.load(f)

        assert "Destroy the One Ring" in data
        assert data["Destroy the One Ring"]["giver"] == "Gandalf"
        assert data["Destroy the One Ring"]["status"] == "active"


class TestSaveEncounters:
    """Tests for encounter saving."""

    def test_save_encounters_single(self, split_storage, sample_encounter):
        """Test saving a single encounter."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.encounters[sample_encounter.name] = sample_encounter

        split_storage._save_encounters(force=True)

        enc_file = split_storage._get_campaign_dir() / "encounters.json"
        with open(enc_file, 'r') as f:
            data = json.load(f)

        assert "Orc Ambush" in data
        assert data["Orc Ambush"]["difficulty"] == "medium"
        assert data["Orc Ambush"]["experience_value"] == 1000


class TestSaveGameState:
    """Tests for game state saving."""

    def test_save_game_state(self, split_storage):
        """Test saving game state."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        campaign.game_state.current_session = 5
        campaign.game_state.party_level = 10
        campaign.game_state.party_funds = "1000 gp"

        split_storage._save_game_state(force=True)

        state_file = split_storage._get_campaign_dir() / "game_state.json"
        with open(state_file, 'r') as f:
            data = json.load(f)

        assert data["current_session"] == 5
        assert data["party_level"] == 10
        assert data["party_funds"] == "1000 gp"


class TestSaveCampaignMetadata:
    """Tests for campaign metadata saving."""

    def test_save_campaign_metadata(self, split_storage):
        """Test that only metadata is saved, not data fields."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="A test campaign",
            dm_name="DM Dave"
        )

        # Add some data
        char = Character(
            name="TestChar",
            character_class=CharacterClass(name="Fighter", level=1, hit_dice="1d10"),
            race=Race(name="Human")
        )
        campaign.characters[char.name] = char

        split_storage._save_campaign_metadata(force=True)

        metadata_file = split_storage._get_campaign_dir() / "campaign.json"
        with open(metadata_file, 'r') as f:
            data = json.load(f)

        # Should have metadata fields
        assert data["name"] == "Test Campaign"
        assert data["description"] == "A test campaign"
        assert data["dm_name"] == "DM Dave"

        # Should NOT have data fields
        assert "characters" not in data
        assert "npcs" not in data
        assert "locations" not in data


class TestSaveSessions:
    """Tests for session saving."""

    def test_save_session_single(self, split_storage, sample_session):
        """Test saving a single session."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.sessions.append(sample_session)

        split_storage._save_session(sample_session, force=True)

        session_file = split_storage._get_campaign_dir() / "sessions" / "session-001.json"
        assert session_file.exists()

        with open(session_file, 'r') as f:
            data = json.load(f)

        assert data["session_number"] == 1
        assert data["title"] == "The Adventure Begins"

    def test_save_session_multiple(self, split_storage, sample_session):
        """Test saving multiple sessions."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        session2 = SessionNote(
            session_number=2,
            title="The Plot Thickens",
            summary="The party discovers a conspiracy",
            events=["Found clues", "Interrogated suspect"],
            characters_present=["Gandalf", "Aragorn"]
        )

        campaign.sessions.append(sample_session)
        campaign.sessions.append(session2)

        split_storage._save_session(sample_session, force=True)
        split_storage._save_session(session2, force=True)

        sessions_dir = split_storage._get_campaign_dir() / "sessions"
        assert (sessions_dir / "session-001.json").exists()
        assert (sessions_dir / "session-002.json").exists()


class TestSaveAll:
    """Tests for save_all method."""

    def test_save_all_complete_campaign(self, split_storage, sample_character,
                                        sample_npc, sample_location, sample_quest,
                                        sample_encounter, sample_session):
        """Test saving all campaign data at once."""
        campaign = split_storage.create_campaign(
            name="Complete Campaign",
            description="A campaign with all data types"
        )

        # Add all types of data
        campaign.characters[sample_character.name] = sample_character
        campaign.npcs[sample_npc.name] = sample_npc
        campaign.locations[sample_location.name] = sample_location
        campaign.quests[sample_quest.title] = sample_quest
        campaign.encounters[sample_encounter.name] = sample_encounter
        campaign.sessions.append(sample_session)

        split_storage.save_all(force=True)

        campaign_dir = split_storage._get_campaign_dir()

        # Verify all files exist
        assert (campaign_dir / "campaign.json").exists()
        assert (campaign_dir / "characters.json").exists()
        assert (campaign_dir / "npcs.json").exists()
        assert (campaign_dir / "locations.json").exists()
        assert (campaign_dir / "quests.json").exists()
        assert (campaign_dir / "encounters.json").exists()
        assert (campaign_dir / "game_state.json").exists()
        assert (campaign_dir / "sessions" / "session-001.json").exists()


class TestLoadCharacters:
    """Tests for character loading."""

    def test_load_characters_empty(self, split_storage):
        """Test loading empty characters file."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        split_storage.save_all(force=True)

        campaign_dir = split_storage._get_campaign_dir()
        characters = split_storage._load_characters(campaign_dir)

        assert characters == {}

    def test_load_characters_single(self, split_storage, sample_character):
        """Test loading a single character."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )
        campaign.characters[sample_character.name] = sample_character
        split_storage.save_all(force=True)

        campaign_dir = split_storage._get_campaign_dir()
        characters = split_storage._load_characters(campaign_dir)

        assert len(characters) == 1
        assert "Gandalf" in characters
        assert characters["Gandalf"].name == "Gandalf"
        assert characters["Gandalf"].player_name == "John"

    def test_load_characters_missing_file(self, split_storage):
        """Test loading when characters file doesn't exist."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        # Remove characters file
        char_file = split_storage._get_campaign_dir() / "characters.json"
        if char_file.exists():
            char_file.unlink()

        campaign_dir = split_storage._get_campaign_dir()
        characters = split_storage._load_characters(campaign_dir)

        assert characters == {}


class TestLoadCampaign:
    """Tests for campaign loading."""

    def test_load_campaign_basic(self, split_storage):
        """Test loading a basic campaign."""
        # Create and save campaign
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="A test campaign"
        )
        original_id = campaign.id

        # Create new storage instance and load
        new_storage = SplitStorageBackend(data_dir=split_storage.data_dir)
        loaded_campaign = new_storage.load_campaign("Test Campaign")

        assert loaded_campaign.name == "Test Campaign"
        assert loaded_campaign.description == "A test campaign"
        assert loaded_campaign.id == original_id

    def test_load_campaign_with_all_data(self, split_storage, sample_character,
                                         sample_npc, sample_location, sample_quest,
                                         sample_encounter, sample_session):
        """Test loading a campaign with all data types."""
        # Create campaign with all data
        campaign = split_storage.create_campaign(
            name="Full Campaign",
            description="Campaign with all data"
        )
        campaign.characters[sample_character.name] = sample_character
        campaign.npcs[sample_npc.name] = sample_npc
        campaign.locations[sample_location.name] = sample_location
        campaign.quests[sample_quest.title] = sample_quest
        campaign.encounters[sample_encounter.name] = sample_encounter
        campaign.sessions.append(sample_session)
        split_storage.save_all(force=True)

        # Load in new storage instance
        new_storage = SplitStorageBackend(data_dir=split_storage.data_dir)
        loaded = new_storage.load_campaign("Full Campaign")

        assert len(loaded.characters) == 1
        assert len(loaded.npcs) == 1
        assert len(loaded.locations) == 1
        assert len(loaded.quests) == 1
        assert len(loaded.encounters) == 1
        assert len(loaded.sessions) == 1

    def test_load_campaign_not_found(self, split_storage):
        """Test loading a non-existent campaign raises error."""
        with pytest.raises(FileNotFoundError, match="not found"):
            split_storage.load_campaign("NonExistent Campaign")


class TestListCampaigns:
    """Tests for listing campaigns."""

    def test_list_campaigns_empty(self, split_storage):
        """Test listing when no campaigns exist."""
        campaigns = split_storage.list_campaigns()
        assert campaigns == []

    def test_list_campaigns_single(self, split_storage):
        """Test listing a single campaign."""
        split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        campaigns = split_storage.list_campaigns()
        assert len(campaigns) == 1
        assert "Test Campaign" in campaigns

    def test_list_campaigns_multiple(self, split_storage):
        """Test listing multiple campaigns."""
        split_storage.create_campaign(name="Campaign 1", description="First")
        split_storage.create_campaign(name="Campaign 2", description="Second")
        split_storage.create_campaign(name="Campaign 3", description="Third")

        campaigns = split_storage.list_campaigns()
        assert len(campaigns) == 3
        assert "Campaign 1" in campaigns
        assert "Campaign 2" in campaigns
        assert "Campaign 3" in campaigns


class TestLoadCurrentCampaign:
    """Tests for loading the most recent campaign."""

    def test_load_most_recent_campaign(self, split_storage):
        """Test that the most recently modified campaign is loaded."""
        import time

        # Create first campaign
        split_storage.create_campaign(name="Old Campaign", description="Old")
        time.sleep(0.01)

        # Create second campaign (more recent)
        split_storage.create_campaign(name="New Campaign", description="New")

        # Create new storage instance (should load most recent)
        new_storage = SplitStorageBackend(data_dir=split_storage.data_dir)

        # Should have loaded the newer campaign
        assert new_storage._current_campaign is not None
        assert new_storage._current_campaign.name == "New Campaign"


class TestGetCurrentCampaign:
    """Tests for getting current campaign."""

    def test_get_current_campaign_none(self, split_storage):
        """Test getting current campaign when none is loaded."""
        assert split_storage.get_current_campaign() is None

    def test_get_current_campaign_after_create(self, split_storage):
        """Test getting current campaign after creation."""
        campaign = split_storage.create_campaign(
            name="Test Campaign",
            description="Test"
        )

        current = split_storage.get_current_campaign()
        assert current == campaign
        assert current.name == "Test Campaign"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
