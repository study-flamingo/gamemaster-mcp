"""
Comprehensive unit tests for SplitStorageBackend class.

Tests cover:
- Campaign directory structure creation and validation
- Loading campaign metadata and data sections
- Dirty tracking and incremental saves
- Atomic write operations
- Session numbering and file management
- Error handling for missing/corrupt files
"""

import json
import pytest
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from gamemaster_mcp.storage import SplitStorageBackend, new_uuid
from gamemaster_mcp.models import (
    Campaign, Character, NPC, Location, Quest, CombatEncounter,
    SessionNote, GameState, CharacterClass, Race, AbilityScore
)


# Test fixtures
@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def split_backend(temp_storage_dir: Path) -> SplitStorageBackend:
    """Create a SplitStorageBackend instance with auto_load disabled."""
    return SplitStorageBackend(data_dir=temp_storage_dir, auto_load=False)


@pytest.fixture
def sample_character() -> Character:
    """Create a sample character for testing."""
    return Character(
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
        description="A wise and powerful wizard",
        bio="One of the five Istari sent to Middle-earth",
    )


@pytest.fixture
def sample_npc() -> NPC:
    """Create a sample NPC for testing."""
    return NPC(
        name="Saruman",
        race="Maiar",
        occupation="Wizard",
        location="Isengard",
        attitude="hostile",
        description="A corrupted wizard",
        bio="Once the head of the White Council",
    )


@pytest.fixture
def sample_location() -> Location:
    """Create a sample location for testing."""
    return Location(
        name="Rivendell",
        location_type="city",
        description="An elven stronghold",
        population=1000,
        government="Council of the Wise",
        notable_features=["Healing halls", "Library", "Council chamber"],
    )


@pytest.fixture
def sample_quest() -> Quest:
    """Create a sample quest for testing."""
    return Quest(
        title="Destroy the One Ring",
        description="Take the ring to Mount Doom and destroy it",
        status="active",
        objectives=["Travel to Mordor", "Reach Mount Doom", "Cast the ring into the fire"],
        rewards=["Save Middle-earth"],
    )


@pytest.fixture
def sample_session() -> SessionNote:
    """Create a sample session note for testing."""
    return SessionNote(
        session_number=1,
        date=datetime.now(),
        title="The Council of Elrond",
        summary="The fellowship is formed",
        key_events=["Frodo volunteers", "Fellowship formed"],
    )


class TestCampaignStructureCreation:
    """Tests for campaign directory structure creation and validation."""

    def test_create_campaign_structure(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test creating directory structure for a new campaign."""
        campaign_name = "Test Campaign"
        split_backend._ensure_campaign_structure(campaign_name)

        campaign_dir = temp_storage_dir / "campaigns" / campaign_name
        assert campaign_dir.exists()
        assert campaign_dir.is_dir()

        sessions_dir = campaign_dir / "sessions"
        assert sessions_dir.exists()
        assert sessions_dir.is_dir()

    def test_create_campaign_with_metadata(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test creating a new campaign with metadata file."""
        campaign = split_backend.create_campaign(
            name="Middle-earth Campaign",
            description="A Lord of the Rings campaign",
            dm_name="Tolkien",
            setting="Middle-earth in the Third Age",
        )

        assert campaign.name == "Middle-earth Campaign"
        assert campaign.description == "A Lord of the Rings campaign"
        assert campaign.dm_name == "Tolkien"
        assert campaign.setting == "Middle-earth in the Third Age"

        # Verify campaign.json exists
        campaign_dir = temp_storage_dir / "campaigns" / "Middle-earth Campaign"
        campaign_file = campaign_dir / "campaign.json"
        assert campaign_file.exists()

        # Verify metadata content
        with open(campaign_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        assert metadata["name"] == "Middle-earth Campaign"
        assert metadata["description"] == "A Lord of the Rings campaign"
        assert metadata["dm_name"] == "Tolkien"

    def test_ensure_campaign_structure_idempotent(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test that ensuring campaign structure multiple times is safe."""
        campaign_name = "Idempotent Test"

        # Create structure twice
        split_backend._ensure_campaign_structure(campaign_name)
        split_backend._ensure_campaign_structure(campaign_name)

        campaign_dir = temp_storage_dir / "campaigns" / campaign_name
        assert campaign_dir.exists()
        assert campaign_dir.is_dir()


class TestLoadCampaignData:
    """Tests for loading campaign metadata and data sections."""

    def test_load_campaign_metadata(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test loading campaign metadata from campaign.json."""
        # Create a campaign first
        campaign = split_backend.create_campaign(
            name="Test Load Campaign",
            description="Testing metadata loading",
            dm_name="Test DM",
        )

        # Load metadata
        campaign_dir = temp_storage_dir / "campaigns" / "Test Load Campaign"
        metadata = split_backend._load_campaign_metadata(campaign_dir)

        assert metadata["name"] == "Test Load Campaign"
        assert metadata["description"] == "Testing metadata loading"
        assert metadata["dm_name"] == "Test DM"
        assert "id" in metadata
        assert "created_at" in metadata

    def test_load_full_campaign(
        self,
        split_backend: SplitStorageBackend,
        sample_character: Character,
        sample_npc: NPC,
        sample_location: Location,
        sample_quest: Quest,
    ) -> None:
        """Test loading a full campaign with all data sections."""
        # Create and populate campaign
        campaign = split_backend.create_campaign(
            name="Full Campaign Test",
            description="Testing full load",
        )

        split_backend._current_campaign = campaign
        campaign.characters["Gandalf"] = sample_character
        campaign.npcs["Saruman"] = sample_npc
        campaign.locations["Rivendell"] = sample_location
        campaign.quests["Destroy the One Ring"] = sample_quest

        # Save all data
        split_backend.save_all(force=True)

        # Create new backend and load campaign
        new_backend = SplitStorageBackend(
            data_dir=split_backend.data_dir, auto_load=False
        )
        loaded_campaign = new_backend.load_campaign("Full Campaign Test")

        assert loaded_campaign.name == "Full Campaign Test"
        assert "Gandalf" in loaded_campaign.characters
        assert "Saruman" in loaded_campaign.npcs
        assert "Rivendell" in loaded_campaign.locations
        assert "Destroy the One Ring" in loaded_campaign.quests

        # Verify character data
        loaded_char = loaded_campaign.characters["Gandalf"]
        assert loaded_char.name == "Gandalf"
        assert loaded_char.player_name == "Alice"
        assert loaded_char.character_class.level == 20

    def test_load_campaign_with_missing_sections(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test loading a campaign with some missing data sections."""
        # Create campaign structure manually with only metadata
        campaign_name = "Minimal Campaign"
        campaign_dir = temp_storage_dir / "campaigns" / campaign_name
        campaign_dir.mkdir(parents=True)

        metadata = {
            "id": new_uuid(),
            "name": campaign_name,
            "description": "A minimal campaign",
            "dm_name": None,
            "setting": None,
            "world_notes": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": None,
        }

        with open(campaign_dir / "campaign.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        # Load campaign (should not fail)
        campaign = split_backend.load_campaign(campaign_name)

        assert campaign.name == campaign_name
        assert len(campaign.characters) == 0
        assert len(campaign.npcs) == 0
        assert len(campaign.locations) == 0
        assert len(campaign.quests) == 0

    def test_load_nonexistent_campaign_raises_error(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test that loading a non-existent campaign raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Campaign 'Nonexistent' not found"):
            split_backend.load_campaign("Nonexistent")


class TestDirtyTracking:
    """Tests for dirty tracking and incremental saves."""

    def test_save_only_dirty_sections(
        self,
        split_backend: SplitStorageBackend,
        sample_character: Character,
        sample_npc: NPC,
    ) -> None:
        """Test that only modified sections are written to disk."""
        # Create and save campaign
        campaign = split_backend.create_campaign(
            name="Dirty Test Campaign",
            description="Testing dirty tracking",
        )
        split_backend._current_campaign = campaign
        campaign.characters["Gandalf"] = sample_character
        split_backend.save_all(force=True)

        # Get initial modification time of characters.json
        campaign_dir = split_backend._get_campaign_dir()
        char_file = campaign_dir / "characters.json"
        initial_mtime = char_file.stat().st_mtime

        # Modify NPCs only (not characters)
        time.sleep(0.01)  # Ensure time difference
        campaign.npcs["Saruman"] = sample_npc
        split_backend._save_npcs(force=True)

        # Characters file should not be modified
        assert char_file.stat().st_mtime == initial_mtime

        # NPCs file should exist and be newer
        npc_file = campaign_dir / "npcs.json"
        assert npc_file.exists()
        assert npc_file.stat().st_mtime > initial_mtime

    def test_unchanged_section_not_saved(
        self, split_backend: SplitStorageBackend, sample_character: Character
    ) -> None:
        """Test that unchanged sections are not re-saved."""
        campaign = split_backend.create_campaign(
            name="Unchanged Test",
            description="Testing unchanged detection",
        )
        split_backend._current_campaign = campaign
        campaign.characters["Gandalf"] = sample_character
        split_backend.save_all(force=True)

        # Get initial modification time
        campaign_dir = split_backend._get_campaign_dir()
        char_file = campaign_dir / "characters.json"
        initial_mtime = char_file.stat().st_mtime

        # Try to save again without changes (should skip)
        time.sleep(0.01)  # Ensure time difference would be detectable
        split_backend._save_characters(force=False)

        # File should not be modified
        assert char_file.stat().st_mtime == initial_mtime

    def test_force_save_overwrites_dirty_check(
        self, split_backend: SplitStorageBackend, sample_character: Character
    ) -> None:
        """Test that force=True bypasses dirty checking."""
        campaign = split_backend.create_campaign(
            name="Force Save Test",
            description="Testing force save",
        )
        split_backend._current_campaign = campaign
        campaign.characters["Gandalf"] = sample_character
        split_backend.save_all(force=True)

        # Get initial modification time
        campaign_dir = split_backend._get_campaign_dir()
        char_file = campaign_dir / "characters.json"
        initial_mtime = char_file.stat().st_mtime

        # Force save without changes
        time.sleep(0.01)
        split_backend._save_characters(force=True)

        # File should be modified
        assert char_file.stat().st_mtime > initial_mtime


class TestAtomicWrites:
    """Tests for atomic write operations."""

    def test_atomic_write_creates_temp_file(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test that atomic writes use a temporary file."""
        test_file = temp_storage_dir / "test_atomic.json"
        test_data = {"test": "data"}

        split_backend._atomic_write(test_file, test_data)

        # Verify file exists and contains correct data
        assert test_file.exists()
        with open(test_file, "r", encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

        # Verify temp file was cleaned up
        temp_file = test_file.with_suffix(".tmp")
        assert not temp_file.exists()

    def test_atomic_write_handles_errors(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test that atomic write cleans up on error."""
        # Create a read-only directory to trigger write error
        test_dir = temp_storage_dir / "readonly_dir"
        test_dir.mkdir()
        test_file = test_dir / "file.json"

        # Make directory read-only on Unix systems
        import os
        import stat
        os.chmod(test_dir, stat.S_IRUSR | stat.S_IXUSR)

        test_data = {"test": "data"}

        # Attempt atomic write (should raise PermissionError or OSError)
        try:
            with pytest.raises((PermissionError, OSError)):
                split_backend._atomic_write(test_file, test_data)
        finally:
            # Restore write permissions for cleanup
            os.chmod(test_dir, stat.S_IRWXU)


class TestSessionManagement:
    """Tests for session numbering and file management."""

    def test_save_new_session(
        self, split_backend: SplitStorageBackend, sample_session: SessionNote
    ) -> None:
        """Test saving a new session with correct numbering."""
        campaign = split_backend.create_campaign(
            name="Session Test Campaign",
            description="Testing session saves",
        )
        split_backend._current_campaign = campaign

        # Add session to campaign
        campaign.sessions.append(sample_session)
        split_backend._save_session(sample_session, force=True)

        # Verify session file exists with correct name
        campaign_dir = split_backend._get_campaign_dir()
        session_file = campaign_dir / "sessions" / "session-001.json"
        assert session_file.exists()

        # Verify content
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)
        assert session_data["session_number"] == 1
        assert session_data["title"] == "The Council of Elrond"

    def test_list_sessions_from_directory(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test loading sessions from sessions/ directory."""
        campaign = split_backend.create_campaign(
            name="List Sessions Test",
            description="Testing session listing",
        )
        split_backend._current_campaign = campaign

        # Create multiple sessions
        for i in range(1, 4):
            session = SessionNote(
                session_number=i,
                date=datetime.now(),
                title=f"Session {i}",
                summary=f"Summary of session {i}",
            )
            campaign.sessions.append(session)
            split_backend._save_session(session, force=True)

        # Load sessions
        campaign_dir = split_backend._get_campaign_dir()
        loaded_sessions = split_backend._load_sessions(campaign_dir)

        assert len(loaded_sessions) == 3
        assert loaded_sessions[0].session_number == 1
        assert loaded_sessions[1].session_number == 2
        assert loaded_sessions[2].session_number == 3

    def test_session_numbering_with_gaps(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test session loading with non-sequential numbering."""
        campaign = split_backend.create_campaign(
            name="Gap Test Campaign",
            description="Testing session gaps",
        )
        split_backend._current_campaign = campaign

        # Create sessions with gaps
        for i in [1, 3, 5]:
            session = SessionNote(
                session_number=i,
                date=datetime.now(),
                title=f"Session {i}",
                summary=f"Summary {i}",
            )
            campaign.sessions.append(session)
            split_backend._save_session(session, force=True)

        # Load and verify
        campaign_dir = split_backend._get_campaign_dir()
        loaded_sessions = split_backend._load_sessions(campaign_dir)

        assert len(loaded_sessions) == 3
        session_numbers = [s.session_number for s in loaded_sessions]
        assert session_numbers == [1, 3, 5]


class TestErrorHandling:
    """Tests for error handling with missing or corrupt files."""

    def test_invalid_campaign_structure_missing_metadata(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test handling of campaign directory without campaign.json."""
        # Create directory without campaign.json
        campaign_dir = temp_storage_dir / "campaigns" / "Invalid Campaign"
        campaign_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="Campaign metadata file not found"):
            split_backend._load_campaign_metadata(campaign_dir)

    def test_corrupt_json_file_handling(
        self, split_backend: SplitStorageBackend, temp_storage_dir: Path
    ) -> None:
        """Test handling of corrupt JSON files."""
        campaign = split_backend.create_campaign(
            name="Corrupt Test",
            description="Testing corrupt file handling",
        )
        split_backend._current_campaign = campaign

        # Create corrupt characters.json
        campaign_dir = split_backend._get_campaign_dir()
        char_file = campaign_dir / "characters.json"
        with open(char_file, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json }")

        # Attempt to load characters (should return empty dict)
        characters = split_backend._load_characters(campaign_dir)
        assert characters == {}

    def test_load_sessions_with_corrupt_file(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test that corrupt session files are skipped gracefully."""
        campaign = split_backend.create_campaign(
            name="Corrupt Session Test",
            description="Testing corrupt session handling",
        )
        split_backend._current_campaign = campaign

        # Create valid and corrupt session files
        campaign_dir = split_backend._get_campaign_dir()
        sessions_dir = campaign_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)

        # Valid session
        valid_session = SessionNote(
            session_number=1,
            date=datetime.now(),
            title="Valid Session",
            summary="This one is valid",
        )
        split_backend._save_session(valid_session, force=True)

        # Corrupt session file
        corrupt_file = sessions_dir / "session-002.json"
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write("{ corrupt json }")

        # Load sessions (should load only valid one)
        loaded_sessions = split_backend._load_sessions(campaign_dir)
        assert len(loaded_sessions) == 1
        assert loaded_sessions[0].session_number == 1


class TestConcurrentAccess:
    """Tests for handling multiple reads safely."""

    def test_concurrent_reads_safe(
        self, split_backend: SplitStorageBackend, sample_character: Character
    ) -> None:
        """Test that multiple reads do not interfere with each other."""
        # Create and save campaign
        campaign = split_backend.create_campaign(
            name="Concurrent Test",
            description="Testing concurrent reads",
        )
        split_backend._current_campaign = campaign
        campaign.characters["Gandalf"] = sample_character
        split_backend.save_all(force=True)

        # Create multiple backend instances and load simultaneously
        backend1 = SplitStorageBackend(
            data_dir=split_backend.data_dir, auto_load=False
        )
        backend2 = SplitStorageBackend(
            data_dir=split_backend.data_dir, auto_load=False
        )

        campaign1 = backend1.load_campaign("Concurrent Test")
        campaign2 = backend2.load_campaign("Concurrent Test")

        # Both should load successfully
        assert campaign1.name == "Concurrent Test"
        assert campaign2.name == "Concurrent Test"
        assert "Gandalf" in campaign1.characters
        assert "Gandalf" in campaign2.characters


class TestHashComputation:
    """Tests for section hash computation for dirty tracking."""

    def test_compute_section_hash_consistent(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test that hash computation is consistent for same data."""
        data = {"name": "Gandalf", "level": 20}

        hash1 = split_backend._compute_section_hash(data)
        hash2 = split_backend._compute_section_hash(data)

        assert hash1 == hash2

    def test_compute_section_hash_different_for_changes(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test that hash changes when data changes."""
        data1 = {"name": "Gandalf", "level": 20}
        data2 = {"name": "Gandalf", "level": 21}

        hash1 = split_backend._compute_section_hash(data1)
        hash2 = split_backend._compute_section_hash(data2)

        assert hash1 != hash2

    def test_compute_section_hash_order_independent(
        self, split_backend: SplitStorageBackend
    ) -> None:
        """Test that hash is independent of dict key order."""
        data1 = {"name": "Gandalf", "level": 20, "class": "Wizard"}
        data2 = {"level": 20, "class": "Wizard", "name": "Gandalf"}

        hash1 = split_backend._compute_section_hash(data1)
        hash2 = split_backend._compute_section_hash(data2)

        # Should be equal due to sort_keys=True in JSON serialization
        assert hash1 == hash2
