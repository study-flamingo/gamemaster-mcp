#!/usr/bin/env python3
"""
Migration utility to convert monolithic campaign files to split directory structure.

This script converts existing single-file campaign JSON files to the new split storage
format, where data is organized across multiple files in a directory structure.

Usage:
    python scripts/migrate_campaign.py "Campaign Name" --backup --dry-run

The script:
1. Loads the monolithic campaign file (campaigns/{name}.json)
2. Extracts data into separate sections
3. Creates a new directory structure (campaigns/{name}/)
4. Writes individual JSON files for each section
5. Optionally backs up the original file

Author: Gamemaster MCP Team
License: MIT
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


class MigrationError(Exception):
    """Custom exception for migration errors."""
    pass


class CampaignMigrator:
    """Handles migration of campaign data from monolithic to split format."""

    def __init__(
        self,
        campaign_name: str,
        data_dir: Path,
        backup: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ):
        """Initialize migrator with configuration.

        Args:
            campaign_name: Name of the campaign to migrate
            data_dir: Base data directory path
            backup: Whether to keep original file as .json.bak
            force: Whether to overwrite existing split directory
            dry_run: Whether to show what would be done without making changes
        """
        self.campaign_name = campaign_name
        self.data_dir = data_dir
        self.backup = backup
        self.force = force
        self.dry_run = dry_run

        self.safe_name = self._sanitize_name(campaign_name)
        self.monolithic_file = data_dir / "campaigns" / f"{self.safe_name}.json"
        self.split_dir = data_dir / "campaigns" / self.safe_name

        # Track what was created for rollback
        self._created_files: list[Path] = []
        self._created_dirs: list[Path] = []

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize campaign name for filesystem use.

        Args:
            name: Raw campaign name

        Returns:
            Sanitized name safe for filesystem
        """
        return "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', "'")).rstrip()

    def _compute_hash(self, data: dict | list) -> str:
        """Compute SHA-256 hash of data for verification.

        Args:
            data: Data to hash

        Returns:
            Hex string of SHA-256 hash
        """
        return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _atomic_write(self, file_path: Path, data: dict | list) -> None:
        """Write data to file atomically (write to temp, then rename).

        Args:
            file_path: Path to the file to write
            data: Data to write (will be JSON serialized)
        """
        if self.dry_run:
            size = len(json.dumps(data, indent=2, default=str).encode())
            print(f"  [DRY RUN] Would write {file_path.name} ({size:,} bytes)")
            return

        temp_file = file_path.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            temp_file.replace(file_path)
            self._created_files.append(file_path)
            print(f"  ✓ Wrote {file_path.name}")
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise MigrationError(f"Failed to write {file_path.name}: {e}")

    def _validate_inputs(self) -> None:
        """Validate that migration can proceed.

        Raises:
            MigrationError: If validation fails
        """
        # Check monolithic file exists
        if not self.monolithic_file.exists():
            raise MigrationError(
                f"Monolithic campaign file not found: {self.monolithic_file}"
            )

        # Check split directory doesn't exist (unless --force)
        if self.split_dir.exists() and not self.force:
            raise MigrationError(
                f"Split directory already exists: {self.split_dir}\n"
                f"Use --force to overwrite"
            )

        # Check file is readable
        try:
            with open(self.monolithic_file, 'r', encoding='utf-8') as f:
                f.read(1)
        except PermissionError:
            raise MigrationError(
                f"Permission denied reading: {self.monolithic_file}"
            )

    def _load_monolithic_file(self) -> dict[str, Any]:
        """Load and validate the monolithic campaign file.

        Returns:
            Campaign data dictionary

        Raises:
            MigrationError: If file cannot be loaded or is invalid
        """
        print(f"\n📂 Loading monolithic file: {self.monolithic_file.name}")

        try:
            with open(self.monolithic_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise MigrationError(f"Invalid JSON in campaign file: {e}")

        # Validate required fields
        required_fields = ['id', 'name', 'description']
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise MigrationError(
                f"Campaign file missing required fields: {', '.join(missing)}"
            )

        # Report stats
        file_size = self.monolithic_file.stat().st_size
        print(f"  ✓ Loaded campaign: {data['name']}")
        print(f"  ✓ File size: {file_size:,} bytes")

        # Count elements
        stats = {
            'characters': len(data.get('characters', {})),
            'npcs': len(data.get('npcs', {})),
            'locations': len(data.get('locations', {})),
            'quests': len(data.get('quests', {})),
            'encounters': len(data.get('encounters', {})),
            'sessions': len(data.get('sessions', [])),
        }
        print(f"  ✓ Data counts: {', '.join(f'{k}={v}' for k, v in stats.items())}")

        return data

    def _create_split_structure(self) -> None:
        """Create the split directory structure.

        Raises:
            MigrationError: If directory creation fails
        """
        if self.dry_run:
            print(f"\n📁 [DRY RUN] Would create directory: {self.split_dir}")
            print(f"📁 [DRY RUN] Would create subdirectory: {self.split_dir}/sessions")
            return

        print(f"\n📁 Creating split directory structure")

        # Remove existing directory if --force
        if self.split_dir.exists() and self.force:
            print(f"  ⚠ Removing existing directory (--force)")
            shutil.rmtree(self.split_dir)

        try:
            self.split_dir.mkdir(parents=True, exist_ok=True)
            self._created_dirs.append(self.split_dir)
            print(f"  ✓ Created: {self.split_dir}")

            sessions_dir = self.split_dir / "sessions"
            sessions_dir.mkdir(exist_ok=True)
            self._created_dirs.append(sessions_dir)
            print(f"  ✓ Created: {sessions_dir}")
        except Exception as e:
            raise MigrationError(f"Failed to create directory structure: {e}")

    def _extract_and_write_sections(self, data: dict[str, Any]) -> None:
        """Extract data sections and write to individual files.

        Args:
            data: Full campaign data dictionary
        """
        print(f"\n💾 Writing split files")

        # 1. Campaign metadata
        metadata = {
            "id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "dm_name": data.get("dm_name"),
            "setting": data.get("setting"),
            "world_notes": data.get("world_notes", ""),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
        }
        self._atomic_write(self.split_dir / "campaign.json", metadata)

        # 2. Characters
        characters = data.get("characters", {})
        self._atomic_write(self.split_dir / "characters.json", characters)

        # 3. NPCs
        npcs = data.get("npcs", {})
        self._atomic_write(self.split_dir / "npcs.json", npcs)

        # 4. Locations
        locations = data.get("locations", {})
        self._atomic_write(self.split_dir / "locations.json", locations)

        # 5. Quests
        quests = data.get("quests", {})
        self._atomic_write(self.split_dir / "quests.json", quests)

        # 6. Encounters
        encounters = data.get("encounters", {})
        self._atomic_write(self.split_dir / "encounters.json", encounters)

        # 7. Game state
        game_state = data.get("game_state", {})
        self._atomic_write(self.split_dir / "game_state.json", game_state)

        # 8. Individual session files
        sessions = data.get("sessions", [])
        sessions_dir = self.split_dir / "sessions"
        for session in sessions:
            session_num = session.get("session_number", 0)
            session_file = sessions_dir / f"session-{session_num:03d}.json"
            self._atomic_write(session_file, session)

    def _handle_backup(self) -> None:
        """Backup or remove the original monolithic file.

        Raises:
            MigrationError: If backup/removal fails
        """
        if self.dry_run:
            if self.backup:
                print(f"\n💾 [DRY RUN] Would backup: {self.monolithic_file.name} → {self.monolithic_file.name}.bak")
            else:
                print(f"\n🗑️  [DRY RUN] Would delete: {self.monolithic_file.name}")
            return

        print(f"\n🔄 Handling original file")

        try:
            if self.backup:
                backup_file = self.monolithic_file.with_suffix('.json.bak')
                self.monolithic_file.rename(backup_file)
                print(f"  ✓ Backed up to: {backup_file.name}")
            else:
                self.monolithic_file.unlink()
                print(f"  ✓ Deleted: {self.monolithic_file.name}")
        except Exception as e:
            raise MigrationError(f"Failed to handle original file: {e}")

    def _rollback(self) -> None:
        """Rollback any changes made during failed migration."""
        if self.dry_run:
            return

        print("\n🔙 Rolling back changes...")

        # Remove created files
        for file_path in reversed(self._created_files):
            try:
                if file_path.exists():
                    file_path.unlink()
                    print(f"  ✓ Removed: {file_path}")
            except Exception as e:
                print(f"  ⚠ Failed to remove {file_path}: {e}")

        # Remove created directories
        for dir_path in reversed(self._created_dirs):
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    print(f"  ✓ Removed: {dir_path}")
            except Exception as e:
                print(f"  ⚠ Failed to remove {dir_path}: {e}")

    def migrate(self) -> None:
        """Execute the migration process.

        Raises:
            MigrationError: If migration fails
        """
        print(f"{'='*70}")
        print(f"Campaign Migration Utility")
        print(f"{'='*70}")
        print(f"Campaign: {self.campaign_name}")
        print(f"Data dir: {self.data_dir}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Backup: {'Yes' if self.backup else 'No'}")
        print(f"Force: {'Yes' if self.force else 'No'}")

        try:
            # Step 1: Validate
            print(f"\n{'='*70}")
            print("Step 1: Validation")
            print(f"{'='*70}")
            self._validate_inputs()
            print("  ✓ Validation passed")

            # Step 2: Load monolithic file
            print(f"\n{'='*70}")
            print("Step 2: Load Campaign Data")
            print(f"{'='*70}")
            data = self._load_monolithic_file()

            # Step 3: Create directory structure
            print(f"\n{'='*70}")
            print("Step 3: Create Split Structure")
            print(f"{'='*70}")
            self._create_split_structure()

            # Step 4: Write split files
            print(f"\n{'='*70}")
            print("Step 4: Write Split Files")
            print(f"{'='*70}")
            self._extract_and_write_sections(data)

            # Step 5: Handle original file
            print(f"\n{'='*70}")
            print("Step 5: Handle Original File")
            print(f"{'='*70}")
            self._handle_backup()

            # Success
            print(f"\n{'='*70}")
            if self.dry_run:
                print("✅ DRY RUN COMPLETE - No changes made")
            else:
                print("✅ MIGRATION COMPLETE")
            print(f"{'='*70}")

            if not self.dry_run:
                print(f"\nSplit directory: {self.split_dir}")
                print(f"Files created: {len(self._created_files)}")

        except MigrationError as e:
            print(f"\n❌ Migration failed: {e}", file=sys.stderr)
            if not self.dry_run:
                self._rollback()
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
            if not self.dry_run:
                self._rollback()
            sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Migrate monolithic campaigns to split format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview migration (dry-run)
  python scripts/migrate_campaign.py "My Campaign" --dry-run

  # Migrate with backup
  python scripts/migrate_campaign.py "My Campaign" --backup

  # Force overwrite existing split directory
  python scripts/migrate_campaign.py "My Campaign" --force

  # Custom data directory
  python scripts/migrate_campaign.py "My Campaign" --data-dir /path/to/data
        """,
    )

    parser.add_argument(
        "campaign_name",
        help="Name of the campaign to migrate"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Keep original file as .json.bak (default: delete original)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing split directory"
    )
    parser.add_argument(
        "--data-dir",
        default="dnd_data",
        type=Path,
        help="Data directory path (default: dnd_data)"
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point for the migration script."""
    args = parse_args()

    migrator = CampaignMigrator(
        campaign_name=args.campaign_name,
        data_dir=args.data_dir,
        backup=args.backup,
        force=args.force,
        dry_run=args.dry_run,
    )

    migrator.migrate()


if __name__ == "__main__":
    main()
