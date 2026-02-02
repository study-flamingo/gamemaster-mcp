"""
Tests for the campaign migration utility.

These tests verify the migration logic for converting monolithic campaign
files to the split directory structure.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

# Import the migration script
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from migrate_campaign import CampaignMigrator, MigrationError


class TestCampaignMigrator:
    """Test suite for CampaignMigrator class."""

    def test_sanitize_name_basic(self):
        """Test basic name sanitization."""
        migrator = CampaignMigrator(
            "Test Campaign",
            Path("data"),
            dry_run=True
        )
        assert migrator.safe_name == "Test Campaign"

    def test_sanitize_name_special_chars(self):
        """Test name sanitization with special characters."""
        migrator = CampaignMigrator(
            "L'Ombra sulla Terra di Mezzo",
            Path("data"),
            dry_run=True
        )
        # Apostrophe should be kept
        assert migrator.safe_name == "L'Ombra sulla Terra di Mezzo"

    def test_sanitize_name_invalid_chars(self):
        """Test name sanitization removes invalid characters."""
        test_name = "Test@Campaign#123!"
        migrator = CampaignMigrator(
            test_name,
            Path("data"),
            dry_run=True
        )
        # Should remove @ # !
        assert migrator.safe_name == "TestCampaign123"

    def test_compute_hash_deterministic(self):
        """Test that hash computation is deterministic."""
        migrator = CampaignMigrator(
            "Test",
            Path("data"),
            dry_run=True
        )

        data = {"name": "Test", "id": "123"}
        hash1 = migrator._compute_hash(data)
        hash2 = migrator._compute_hash(data)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars

    def test_compute_hash_different_data(self):
        """Test that different data produces different hashes."""
        migrator = CampaignMigrator(
            "Test",
            Path("data"),
            dry_run=True
        )

        data1 = {"name": "Test1", "id": "123"}
        data2 = {"name": "Test2", "id": "123"}

        hash1 = migrator._compute_hash(data1)
        hash2 = migrator._compute_hash(data2)

        assert hash1 != hash2

    def test_validate_inputs_missing_file(self, tmp_path):
        """Test validation fails when monolithic file doesn't exist."""
        migrator = CampaignMigrator(
            "NonExistent",
            tmp_path,
            dry_run=False
        )

        with pytest.raises(MigrationError, match="not found"):
            migrator._validate_inputs()

    def test_validate_inputs_existing_split_dir(self, tmp_path):
        """Test validation fails when split directory exists without --force."""
        # Create monolithic file
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()
        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text('{"name": "Test", "id": "123"}')

        # Create split directory
        split_dir = campaigns_dir / "Test"
        split_dir.mkdir()

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            force=False,
            dry_run=False
        )

        with pytest.raises(MigrationError, match="already exists"):
            migrator._validate_inputs()

    def test_validate_inputs_with_force(self, tmp_path):
        """Test validation succeeds when split directory exists with --force."""
        # Create monolithic file
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()
        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text('{"name": "Test", "id": "123"}')

        # Create split directory
        split_dir = campaigns_dir / "Test"
        split_dir.mkdir()

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            force=True,
            dry_run=False
        )

        # Should not raise
        migrator._validate_inputs()

    def test_load_monolithic_file_valid(self, tmp_path):
        """Test loading a valid monolithic campaign file."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        campaign_data = {
            "id": "test123",
            "name": "Test Campaign",
            "description": "Test description",
            "characters": {"Alice": {"name": "Alice"}},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": []
        }

        monolithic = campaigns_dir / "Test Campaign.json"
        monolithic.write_text(json.dumps(campaign_data))

        migrator = CampaignMigrator(
            "Test Campaign",
            tmp_path,
            dry_run=True
        )

        loaded_data = migrator._load_monolithic_file()

        assert loaded_data["name"] == "Test Campaign"
        assert loaded_data["id"] == "test123"
        assert "characters" in loaded_data

    def test_load_monolithic_file_invalid_json(self, tmp_path):
        """Test loading fails with invalid JSON."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text("{ invalid json }")

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            dry_run=True
        )

        with pytest.raises(MigrationError, match="Invalid JSON"):
            migrator._load_monolithic_file()

    def test_load_monolithic_file_missing_fields(self, tmp_path):
        """Test loading fails when required fields are missing."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        campaign_data = {
            "id": "test123",
            # Missing 'name' and 'description'
        }

        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text(json.dumps(campaign_data))

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            dry_run=True
        )

        with pytest.raises(MigrationError, match="missing required fields"):
            migrator._load_monolithic_file()

    def test_dry_run_mode_no_changes(self, tmp_path):
        """Test that dry-run mode doesn't create any files."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        campaign_data = {
            "id": "test123",
            "name": "Test",
            "description": "Test description",
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {}
        }

        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text(json.dumps(campaign_data))

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            dry_run=True
        )

        # Perform migration in dry-run mode
        migrator.migrate()

        # Split directory should not be created
        split_dir = campaigns_dir / "Test"
        assert not split_dir.exists()

        # Original file should still exist
        assert monolithic.exists()

    def test_migration_creates_all_files(self, tmp_path):
        """Test that migration creates all expected files."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        campaign_data = {
            "id": "test123",
            "name": "Test",
            "description": "Test description",
            "dm_name": "Alice",
            "setting": "Fantasy",
            "world_notes": "Notes",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "characters": {"Bob": {"name": "Bob"}},
            "npcs": {"NPC1": {"name": "NPC1"}},
            "locations": {"Location1": {"name": "Location1"}},
            "quests": {"Quest1": {"title": "Quest1"}},
            "encounters": {},
            "sessions": [
                {"session_number": 1, "title": "Session 1"},
                {"session_number": 2, "title": "Session 2"}
            ],
            "game_state": {"campaign_name": "Test"}
        }

        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text(json.dumps(campaign_data))

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            backup=True,
            dry_run=False
        )

        migrator.migrate()

        split_dir = campaigns_dir / "Test"

        # Check all expected files exist
        assert (split_dir / "campaign.json").exists()
        assert (split_dir / "characters.json").exists()
        assert (split_dir / "npcs.json").exists()
        assert (split_dir / "locations.json").exists()
        assert (split_dir / "quests.json").exists()
        assert (split_dir / "encounters.json").exists()
        assert (split_dir / "game_state.json").exists()

        # Check session files
        assert (split_dir / "sessions" / "session-001.json").exists()
        assert (split_dir / "sessions" / "session-002.json").exists()

        # Check backup was created
        assert (campaigns_dir / "Test.json.bak").exists()

        # Verify campaign.json content
        with open(split_dir / "campaign.json") as f:
            metadata = json.load(f)
            assert metadata["name"] == "Test"
            assert metadata["id"] == "test123"
            assert "characters" not in metadata  # Should not include data sections

    def test_migration_without_backup(self, tmp_path):
        """Test that migration without backup deletes original file."""
        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        campaign_data = {
            "id": "test123",
            "name": "Test",
            "description": "Test description",
            "characters": {},
            "npcs": {},
            "locations": {},
            "quests": {},
            "encounters": {},
            "sessions": [],
            "game_state": {}
        }

        monolithic = campaigns_dir / "Test.json"
        monolithic.write_text(json.dumps(campaign_data))

        migrator = CampaignMigrator(
            "Test",
            tmp_path,
            backup=False,
            dry_run=False
        )

        migrator.migrate()

        # Original file should be deleted
        assert not monolithic.exists()
        # Backup should not exist
        assert not (campaigns_dir / "Test.json.bak").exists()


class TestCommandLineInterface:
    """Test command-line interface parsing."""

    def test_parse_args_basic(self):
        """Test basic argument parsing."""
        from migrate_campaign import parse_args

        with patch('sys.argv', ['migrate_campaign.py', 'Test Campaign']):
            args = parse_args()
            assert args.campaign_name == 'Test Campaign'
            assert not args.backup
            assert not args.dry_run
            assert not args.force

    def test_parse_args_all_flags(self):
        """Test parsing with all flags enabled."""
        from migrate_campaign import parse_args

        with patch('sys.argv', [
            'migrate_campaign.py',
            'Test Campaign',
            '--backup',
            '--dry-run',
            '--force',
            '--data-dir',
            '/custom/path'
        ]):
            args = parse_args()
            assert args.campaign_name == 'Test Campaign'
            assert args.backup
            assert args.dry_run
            assert args.force
            assert args.data_dir == Path('/custom/path')
