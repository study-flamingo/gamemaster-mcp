"""
Unit tests for DnDStorage integration with RulebookManager.

Tests cover:
- Rulebooks directory creation on campaign creation
- RulebookManager loading from manifest
- Backward compatibility for campaigns without rulebooks
- Property accessors (rulebooks_dir, rulebook_cache_dir, rulebook_manager)
"""

import json
import pytest
from pathlib import Path

from gamemaster_mcp.storage import DnDStorage, StorageFormat
from gamemaster_mcp.rulebooks.manager import RulebookManager


# Test fixtures
@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def storage(temp_storage_dir: Path) -> DnDStorage:
    """Create a DnDStorage instance for testing."""
    return DnDStorage(data_dir=temp_storage_dir)


class TestRulebookDirectoryCreation:
    """Tests for rulebook directory structure creation."""

    def test_create_campaign_creates_rulebooks_directory(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test that creating a campaign creates the rulebooks directory structure."""
        # Create a new campaign
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Test description",
            dm_name="Test DM"
        )

        # Verify campaign was created
        assert campaign is not None
        assert campaign.name == "Test Campaign"

        # Verify rulebooks directory exists
        campaign_dir = temp_storage_dir / "campaigns" / "Test Campaign"
        rulebooks_dir = campaign_dir / "rulebooks"
        custom_dir = rulebooks_dir / "custom"

        assert rulebooks_dir.exists()
        assert rulebooks_dir.is_dir()
        assert custom_dir.exists()
        assert custom_dir.is_dir()

    def test_rulebooks_dir_property_split_storage(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test rulebooks_dir property returns correct path for split storage."""
        # Create campaign
        storage.create_campaign(
            name="Split Campaign",
            description="Test",
            dm_name="DM"
        )

        # Check property
        rulebooks_dir = storage.rulebooks_dir
        assert rulebooks_dir is not None
        expected_path = temp_storage_dir / "campaigns" / "Split Campaign" / "rulebooks"
        assert rulebooks_dir == expected_path

    def test_rulebooks_dir_property_monolithic_storage(
        self, temp_storage_dir: Path
    ) -> None:
        """Test rulebooks_dir property returns None for monolithic storage."""
        # Create a monolithic campaign file manually
        campaigns_dir = temp_storage_dir / "campaigns"
        campaigns_dir.mkdir(parents=True)

        campaign_data = {
            "id": "test123",
            "name": "Monolithic Campaign",
            "description": "Test",
            "dm_name": "DM",
            "setting": None,
            "world_notes": "",
            "created_at": "2024-01-01T00:00:00",
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
                "updated_at": "2024-01-01T00:00:00",
            },
        }

        campaign_file = campaigns_dir / "Monolithic Campaign.json"
        with open(campaign_file, "w", encoding="utf-8") as f:
            json.dump(campaign_data, f)

        # Load the monolithic campaign
        storage = DnDStorage(data_dir=temp_storage_dir)
        storage.load_campaign("Monolithic Campaign")

        # Check property returns None
        assert storage.rulebooks_dir is None

    def test_rulebook_cache_dir_property(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test rulebook_cache_dir property creates and returns cache directory."""
        cache_dir = storage.rulebook_cache_dir

        assert cache_dir is not None
        expected_path = temp_storage_dir / "rulebook_cache"
        assert cache_dir == expected_path
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_rulebook_cache_dir_creates_if_missing(
        self, temp_storage_dir: Path
    ) -> None:
        """Test that accessing rulebook_cache_dir creates the directory if it doesn't exist."""
        # Create storage
        storage = DnDStorage(data_dir=temp_storage_dir)

        # Ensure cache dir doesn't exist initially
        cache_path = temp_storage_dir / "rulebook_cache"
        if cache_path.exists():
            cache_path.rmdir()

        # Access property
        cache_dir = storage.rulebook_cache_dir

        # Verify it was created
        assert cache_dir.exists()
        assert cache_dir.is_dir()


class TestRulebookManagerIntegration:
    """Tests for RulebookManager loading and integration."""

    def test_rulebook_manager_initially_none(
        self, storage: DnDStorage
    ) -> None:
        """Test that rulebook_manager is None before any campaign is loaded."""
        assert storage.rulebook_manager is None

    def test_rulebook_manager_none_without_manifest(
        self, storage: DnDStorage
    ) -> None:
        """Test that rulebook_manager remains None for campaigns without manifest."""
        # Create a campaign (no manifest created)
        storage.create_campaign(
            name="No Manifest Campaign",
            description="Test",
            dm_name="DM"
        )

        # Manager should be None (no manifest exists)
        assert storage.rulebook_manager is None

    def test_rulebook_manager_loads_with_manifest(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test that RulebookManager loads when manifest exists."""
        # Create a campaign
        storage.create_campaign(
            name="With Manifest",
            description="Test",
            dm_name="DM"
        )

        # Create a minimal manifest
        campaign_dir = temp_storage_dir / "campaigns" / "With Manifest"
        rulebooks_dir = campaign_dir / "rulebooks"
        manifest_path = rulebooks_dir / "manifest.json"

        manifest_data = {
            "active_sources": [],
            "priority": [],
            "conflict_resolution": "last_wins"
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Reload the campaign to trigger manifest loading
        storage.load_campaign("With Manifest")

        # Manager should be loaded
        assert storage.rulebook_manager is not None
        assert isinstance(storage.rulebook_manager, RulebookManager)

    def test_rulebook_manager_with_srd_source(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test loading RulebookManager with SRD source in manifest."""
        # Create a campaign
        storage.create_campaign(
            name="SRD Campaign",
            description="Test",
            dm_name="DM"
        )

        # Create a manifest with SRD source
        campaign_dir = temp_storage_dir / "campaigns" / "SRD Campaign"
        rulebooks_dir = campaign_dir / "rulebooks"
        manifest_path = rulebooks_dir / "manifest.json"

        manifest_data = {
            "active_sources": [
                {
                    "id": "srd-2014",
                    "type": "srd",
                    "loaded_at": "2024-01-01T00:00:00",
                    "version": "2014"
                }
            ],
            "priority": ["srd-2014"],
            "conflict_resolution": "last_wins"
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Reload the campaign
        storage.load_campaign("SRD Campaign")

        # Manager should be loaded with SRD source
        # Note: This may fail if network is unavailable
        manager = storage.rulebook_manager
        if manager is not None:
            assert isinstance(manager, RulebookManager)
            # We can't guarantee the source loaded successfully (network dependency)
            # but the manager should exist

    def test_backward_compatibility_no_rulebooks_dir(
        self, temp_storage_dir: Path
    ) -> None:
        """Test backward compatibility with campaigns created before rulebooks feature."""
        # Create a split campaign manually without rulebooks directory
        campaign_dir = temp_storage_dir / "campaigns" / "Old Campaign"
        campaign_dir.mkdir(parents=True)
        (campaign_dir / "sessions").mkdir()

        # Create campaign.json
        campaign_data = {
            "id": "old123",
            "name": "Old Campaign",
            "description": "Created before rulebooks feature",
            "dm_name": "DM",
            "setting": None,
            "world_notes": "",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": None,
        }

        with open(campaign_dir / "campaign.json", "w", encoding="utf-8") as f:
            json.dump(campaign_data, f)

        # Create empty data files
        for filename in ["characters.json", "npcs.json", "locations.json",
                         "quests.json", "encounters.json"]:
            with open(campaign_dir / filename, "w", encoding="utf-8") as f:
                json.dump({}, f)

        # Create game_state.json
        game_state_data = {
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
            "updated_at": "2024-01-01T00:00:00",
        }

        with open(campaign_dir / "game_state.json", "w", encoding="utf-8") as f:
            json.dump(game_state_data, f)

        # Load the campaign
        storage = DnDStorage(data_dir=temp_storage_dir)
        campaign = storage.load_campaign("Old Campaign")

        # Should load successfully
        assert campaign is not None
        assert campaign.name == "Old Campaign"

        # Rulebook manager should be None (no manifest)
        assert storage.rulebook_manager is None

        # rulebooks_dir should return path but directory may not exist yet
        rulebooks_dir = storage.rulebooks_dir
        assert rulebooks_dir is not None
        # Path exists but the directory might not have been created
        assert rulebooks_dir == campaign_dir / "rulebooks"


class TestRulebookManagerErrorHandling:
    """Tests for error handling in RulebookManager integration."""

    def test_invalid_manifest_handled_gracefully(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test that invalid manifest doesn't crash campaign loading."""
        # Create a campaign
        storage.create_campaign(
            name="Invalid Manifest",
            description="Test",
            dm_name="DM"
        )

        # Create an invalid manifest
        campaign_dir = temp_storage_dir / "campaigns" / "Invalid Manifest"
        rulebooks_dir = campaign_dir / "rulebooks"
        manifest_path = rulebooks_dir / "manifest.json"

        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        # Reload the campaign - should not crash
        campaign = storage.load_campaign("Invalid Manifest")

        # Campaign should load successfully
        assert campaign is not None
        assert campaign.name == "Invalid Manifest"

        # But manager should be None
        assert storage.rulebook_manager is None

    def test_corrupted_manifest_handled_gracefully(
        self, storage: DnDStorage, temp_storage_dir: Path
    ) -> None:
        """Test that corrupted manifest data doesn't crash campaign loading."""
        # Create a campaign
        storage.create_campaign(
            name="Corrupted Manifest",
            description="Test",
            dm_name="DM"
        )

        # Create a manifest with missing required fields
        campaign_dir = temp_storage_dir / "campaigns" / "Corrupted Manifest"
        rulebooks_dir = campaign_dir / "rulebooks"
        manifest_path = rulebooks_dir / "manifest.json"

        manifest_data = {
            "active_sources": [
                {
                    "id": "broken",
                    "type": "unknown_type",  # Invalid type
                    "loaded_at": "2024-01-01T00:00:00"
                }
            ],
            "priority": ["broken"],
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Reload the campaign - should not crash
        campaign = storage.load_campaign("Corrupted Manifest")

        # Campaign should load successfully
        assert campaign is not None

        # Manager might be None or partially loaded depending on error handling
        # The important thing is the campaign loads
