"""
Storage layer for the D&D MCP Server.
Handles persistence of campaign data to JSON files.
"""

import asyncio
import logging
import shortuuid
import json
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from .models import (
    Campaign, Character, NPC, Location, Quest, CombatEncounter,
    SessionNote, GameState, AdventureEvent
)
from .rulebooks.manager import RulebookManager

logger = logging.getLogger("gamemaster-mcp")

logging.basicConfig(
    level=logging.DEBUG,
)


# UUID Helper function
def new_uuid() -> str:
    """Generate a new random 8-character UUID."""
    return shortuuid.random(length=8)


# Storage Format Enums
class StorageFormat:
    """Storage format constants for campaign data."""
    MONOLITHIC = "monolithic"  # Single JSON file per campaign
    SPLIT = "split"           # Directory with separate JSON files
    NOT_FOUND = "not_found"   # Campaign doesn't exist yet

class DnDStorage:
    """Handles storage and retrieval of D&D campaign data."""

    def __init__(self, data_dir: str | Path = "dnd_data"):
        self.data_dir = Path(data_dir)
        logger.debug(f"📂 Initializing DnDStorage with data_dir: {self.data_dir.resolve()}")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories if necessary
        (self.data_dir / "campaigns").mkdir(exist_ok=True)
        (self.data_dir / "events").mkdir(exist_ok=True)
        logger.debug("📂 Storage subdirectories ensured.")

        self._current_campaign: Campaign | None = None
        self._events: list[AdventureEvent] = []

        # Performance optimization: indexes for O(1) character lookups
        self._character_id_index: dict[str, str] = {}  # id -> character_name
        self._player_name_index: dict[str, str] = {}  # player_name (lowercase) -> character_name

        # Batch mode flag to defer saves during bulk operations
        self._batch_mode: bool = False

        # Dirty tracking: hash of last saved campaign state
        self._campaign_hash: str = ""

        # Track storage format of current campaign
        self._current_format: str = StorageFormat.NOT_FOUND

        # Initialize split storage backend (without auto-loading campaigns)
        self._split_backend = SplitStorageBackend(data_dir=data_dir, auto_load=False)

        # Rulebook manager for the current campaign
        self._rulebook_manager: RulebookManager | None = None

        # Load existing data
        logger.debug("📂 Loading initial data...")
        self._load_current_campaign()
        self._load_events()
        logger.debug("✅ Initial data loaded.")

    @property
    def rulebook_manager(self) -> RulebookManager | None:
        """Get the rulebook manager for the current campaign."""
        return self._rulebook_manager

    @property
    def rulebooks_dir(self) -> Path | None:
        """Get the rulebooks directory for the current campaign.

        Returns:
            Path to rulebooks directory for split storage campaigns, None otherwise
        """
        if self._current_format == StorageFormat.SPLIT and self._current_campaign:
            campaign_dir = self._split_backend._get_campaign_dir(self._current_campaign.name)
            return campaign_dir / "rulebooks"
        return None

    @property
    def rulebook_cache_dir(self) -> Path:
        """Get the global rulebook cache directory.

        Returns:
            Path to the global cache directory (shared across campaigns)
        """
        cache_dir = self.data_dir / "rulebook_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    def _get_campaign_file(self, campaign_name: str | None = None) -> Path:
        """Get the file path for a campaign."""
        if campaign_name is None and self._current_campaign:
            campaign_name = self._current_campaign.name
        if campaign_name is None:
            raise ValueError("No campaign name provided and no current campaign")

        safe_name = "".join(c for c in campaign_name if c.isalnum() or c in (' ', '-', '_', "'")).rstrip()
        return self.data_dir / "campaigns" / f"{safe_name}.json"

    def _get_events_file(self) -> Path:
        """Get the file path for adventure events."""
        return self.data_dir / "events" / "adventure_log.json"

    def _detect_campaign_format(self, campaign_name: str) -> str:
        """Detect the storage format of a campaign.

        Args:
            campaign_name: The name of the campaign to check

        Returns:
            One of StorageFormat constants: MONOLITHIC, SPLIT, or NOT_FOUND
        """
        safe_name = "".join(c for c in campaign_name if c.isalnum() or c in (' ', '-', '_', "'")).rstrip()

        dir_path = self.data_dir / "campaigns" / safe_name
        file_path = self.data_dir / "campaigns" / f"{safe_name}.json"

        # Check for split format (directory-based)
        if dir_path.is_dir():
            # Verify it has the campaign.json file to confirm it's a valid split campaign
            campaign_file = dir_path / "campaign.json"
            if campaign_file.exists():
                logger.debug(f"📂 Campaign '{campaign_name}' detected as SPLIT format")
                return StorageFormat.SPLIT
            else:
                logger.warning(f"⚠️ Directory exists for '{campaign_name}' but missing campaign.json")

        # Check for monolithic format (single file)
        if file_path.is_file():
            logger.debug(f"📂 Campaign '{campaign_name}' detected as MONOLITHIC format")
            return StorageFormat.MONOLITHIC

        # Campaign doesn't exist
        logger.debug(f"📂 Campaign '{campaign_name}' NOT FOUND")
        return StorageFormat.NOT_FOUND

    def _rebuild_character_index(self) -> None:
        """Rebuild character indexes for O(1) lookups by ID or player name."""
        self._character_id_index.clear()
        self._player_name_index.clear()
        if self._current_campaign:
            for name, char in self._current_campaign.characters.items():
                self._character_id_index[char.id] = name
                if char.player_name:
                    # Index by lowercase player name for case-insensitive matching
                    self._player_name_index[char.player_name.lower()] = name
            logger.debug(f"🔄 Character index rebuilt with {len(self._character_id_index)} ID entries, {len(self._player_name_index)} player entries")

    def _compute_campaign_hash(self) -> str:
        """Compute hash of campaign data for dirty tracking."""
        if not self._current_campaign:
            return ""
        campaign_data = self._current_campaign.model_dump(mode='json')
        return sha256(json.dumps(campaign_data, sort_keys=True).encode()).hexdigest()

    @contextmanager
    def batch_update(self):
        """Context manager for batch operations - defers saves until exit."""
        self._batch_mode = True
        try:
            yield
            # Sync with split backend if using split format
            if self._current_format == StorageFormat.SPLIT and self._current_campaign:
                self._split_backend._current_campaign = self._current_campaign
            self._save_campaign(force=True)  # Single save at the end
        finally:
            self._batch_mode = False

    def _save_campaign(self, force: bool = False) -> None:
        """Save the current campaign to disk using the appropriate format.

        Args:
            force: If True, bypass batch mode and dirty checking.
        """
        if not self._current_campaign:
            logger.debug("❌ No current campaign to save.")
            return

        # Skip save if in batch mode (unless forced)
        if self._batch_mode and not force:
            logger.debug("⏳ Batch mode active, deferring save...")
            return

        # Dirty tracking: skip save if unchanged (unless forced)
        if not force:
            current_hash = self._compute_campaign_hash()
            if current_hash == self._campaign_hash:
                logger.debug("✅ Campaign unchanged, skipping save.")
                return

        # Route to appropriate saver based on current format
        if self._current_format == StorageFormat.MONOLITHIC:
            self._save_monolithic_campaign()
        elif self._current_format == StorageFormat.SPLIT:
            self._save_split_campaign()
        else:
            # Default to monolithic for backward compatibility
            logger.warning(f"⚠️ Unknown storage format '{self._current_format}', defaulting to monolithic")
            self._save_monolithic_campaign()

        # Update hash after successful save
        self._campaign_hash = self._compute_campaign_hash()
        logger.debug(f"✅ Campaign '{self._current_campaign.name}' saved successfully.")

    def _save_monolithic_campaign(self) -> None:
        """Save campaign as a single JSON file (legacy format)."""
        campaign_file = self._get_campaign_file()
        logger.debug(f"💾 Saving campaign '{self._current_campaign.name}' to {campaign_file} (monolithic)")
        logger.info(f"💾 Autosaving '{self._current_campaign.name}'")
        campaign_data = self._current_campaign.model_dump(mode='json')

        with open(campaign_file, 'w', encoding='utf-8') as f:
            json.dump(campaign_data, f, default=str)

    def _save_split_campaign(self) -> None:
        """Save campaign using split directory structure (new format)."""
        if not self._current_campaign:
            return

        logger.debug(f"💾 Saving campaign '{self._current_campaign.name}' using split format")

        # Sync current campaign to split backend
        self._split_backend._current_campaign = self._current_campaign

        # Use split backend to save all files
        self._split_backend.save_all(force=False)

        logger.debug(f"✅ Campaign '{self._current_campaign.name}' saved successfully (split format).")

    def _load_current_campaign(self):
        """Load the most recently used campaign."""
        logger.debug("📂 Attempting to load the most recent campaign...")
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            logger.debug("❌ Campaigns directory does not exist. No campaign loaded.")
            return

        # Find the most recent campaign (file or directory)
        campaign_files = list(campaigns_dir.glob("*.json"))
        campaign_dirs = [d for d in campaigns_dir.iterdir() if d.is_dir()]

        if not campaign_files and not campaign_dirs:
            logger.debug("❌ No campaigns found.")
            return

        # Get most recent from both files and directories
        all_campaigns = []
        if campaign_files:
            all_campaigns.extend(campaign_files)
        if campaign_dirs:
            # For directories, check campaign.json modification time
            for d in campaign_dirs:
                campaign_file = d / "campaign.json"
                if campaign_file.exists():
                    all_campaigns.append(campaign_file)

        if not all_campaigns:
            logger.debug("❌ No valid campaigns found.")
            return

        # Sort by modification time and load the most recent
        latest_file = max(all_campaigns, key=lambda f: f.stat().st_mtime)
        logger.debug(f"📂 Most recent campaign file is '{latest_file.name}'.")

        # Determine campaign name from the file/directory
        if latest_file.name == "campaign.json":
            # Split format: campaign name is the parent directory
            campaign_name = latest_file.parent.name
        else:
            # Monolithic format: campaign name is the file stem
            campaign_name = latest_file.stem

        # Load campaign using the appropriate method
        try:
            self.load_campaign(campaign_name)
        except Exception as e:
            logger.error(f"❌ Error loading campaign '{campaign_name}': {e}")

    def _save_events(self):
        """Save adventure events to disk."""
        events_file = self._get_events_file()
        logger.debug(f"💾 Saving {len(self._events)} events to {events_file}...")
        events_data = [event.model_dump(mode='json') for event in self._events]

        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, default=str)
        logger.debug("✅ Events saved successfully.")

    def _load_events(self):
        """Load adventure events from disk."""
        logger.debug("📂 Attempting to load adventure events...")
        events_file = self._get_events_file()
        if not events_file.exists():
            logger.debug("❌ Adventure log file does not exist. No events loaded.")
            return

        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
            self._events = [AdventureEvent.model_validate(event) for event in events_data]
            logger.info(f"✅ Successfully loaded {len(self._events)} events.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ Error loading events: {e}")

    # Campaign Management
    def create_campaign(self, name: str, description: str, dm_name: str | None = None, setting: str | Path | None = None) -> Campaign:
        """Create a new campaign using split storage format."""
        logger.info(f"✨ Creating new campaign: '{name}'")

        # Use split backend to create the campaign
        campaign = self._split_backend.create_campaign(
            name=name,
            description=description,
            dm_name=dm_name,
            setting=setting
        )

        # Sync to main storage
        self._current_campaign = campaign
        self._current_format = StorageFormat.SPLIT

        # Create rulebooks directory structure
        campaign_dir = self._split_backend._get_campaign_dir(name)
        rulebooks_dir = campaign_dir / "rulebooks"
        rulebooks_dir.mkdir(exist_ok=True)
        (rulebooks_dir / "custom").mkdir(exist_ok=True)
        logger.debug(f"📂 Created rulebooks directory structure at {rulebooks_dir}")

        # Rebuild indexes for new campaign
        self._rebuild_character_index()

        # Update campaign hash
        self._campaign_hash = self._compute_campaign_hash()

        logger.info(f"✅ Campaign '{name}' created and set as active using {self._current_format} format.")
        return campaign

    def get_current_campaign(self) -> Campaign | None:
        """Get the current campaign."""
        return self._current_campaign

    def list_campaigns(self) -> list[str]:
        """List all available campaigns (both monolithic and split formats)."""
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            return []

        campaigns = []

        # Find monolithic campaigns (JSON files)
        for f in campaigns_dir.glob("*.json"):
            campaigns.append(f.stem)

        # Find split campaigns (directories with campaign.json)
        for d in campaigns_dir.iterdir():
            if d.is_dir():
                campaign_file = d / "campaign.json"
                if campaign_file.exists():
                    campaigns.append(d.name)

        return sorted(campaigns)

    def load_campaign(self, name: str) -> Campaign:
        """Load a specific campaign, automatically detecting format."""
        logger.info(f"📂 Attempting to load campaign: '{name}'")

        # Detect storage format
        storage_format = self._detect_campaign_format(name)

        if storage_format == StorageFormat.NOT_FOUND:
            logger.error(f"❌ Campaign '{name}' not found")
            raise FileNotFoundError(f"Campaign '{name}' not found")

        # Route to appropriate loader based on format
        if storage_format == StorageFormat.MONOLITHIC:
            campaign = self._load_monolithic_campaign(name)
        elif storage_format == StorageFormat.SPLIT:
            campaign = self._load_split_campaign(name)
            # Sync split backend with loaded campaign
            self._split_backend._current_campaign = campaign
        else:
            raise ValueError(f"Unknown storage format: {storage_format}")

        self._current_campaign = campaign
        self._current_format = storage_format
        self._rebuild_character_index()
        self._campaign_hash = self._compute_campaign_hash()

        # Load RulebookManager if manifest exists (split campaigns only)
        self._load_rulebook_manager()

        logger.info(f"✅ Successfully loaded campaign '{name}' using {storage_format} format.")
        return self._current_campaign

    def _load_rulebook_manager(self) -> None:
        """Load RulebookManager for the current campaign if manifest exists.

        Only applicable to split storage campaigns. If manifest doesn't exist,
        sets _rulebook_manager to None (backward compatible).
        """
        # Clear any existing manager
        self._rulebook_manager = None

        # Only load for split campaigns
        if self._current_format != StorageFormat.SPLIT or not self._current_campaign:
            return

        # Get campaign directory
        campaign_dir = self._split_backend._get_campaign_dir(self._current_campaign.name)
        manifest_path = campaign_dir / "rulebooks" / "manifest.json"

        # Check if manifest exists
        if not manifest_path.exists():
            logger.debug(f"No rulebook manifest found at {manifest_path}, skipping RulebookManager load")
            return

        # Load manager from manifest (async operation)
        try:
            # Execute the async factory method
            # Use get_event_loop() instead of asyncio.run() to avoid closing the loop
            # which would break subsequent async operations in the same process
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running - get or create one without closing it
                loop = asyncio.get_event_loop()

            self._rulebook_manager = loop.run_until_complete(
                RulebookManager.from_manifest(campaign_dir)
            )
            logger.info(f"✅ Loaded RulebookManager for campaign '{self._current_campaign.name}'")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load RulebookManager: {e}")
            self._rulebook_manager = None

    def _load_monolithic_campaign(self, name: str) -> Campaign:
        """Load a campaign from a single JSON file (legacy format)."""
        campaign_file = self._get_campaign_file(name)
        logger.debug(f"📂 Loading monolithic campaign from: {campaign_file}")

        with open(campaign_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Campaign.model_validate(data)

    def _load_split_campaign(self, name: str) -> Campaign:
        """Load a campaign from split directory structure (new format)."""
        logger.debug(f"📂 Loading split campaign: '{name}'")

        # Use split backend to load campaign
        campaign = self._split_backend.load_campaign(name)

        logger.debug(f"✅ Successfully loaded split campaign: '{name}'")
        return campaign

    def update_campaign(self, **kwargs):
        """Update campaign metadata."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"📝 Updating campaign '{self._current_campaign.name}' with data: {kwargs}")
        for key, value in kwargs.items():
            if hasattr(self._current_campaign, key):
                logger.debug(f"📝 Updating {key} to {value}")
                setattr(self._current_campaign, key, value)

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Campaign '{self._current_campaign.name}' updated.")

    # Character Management
    def add_character(self, character: Character) -> None:
        """Add a character to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"➕ Adding character '{character.name}' to campaign '{self._current_campaign.name}'.")
        self._current_campaign.characters[character.name] = character
        # Update indexes for O(1) lookup by ID and player name
        self._character_id_index[character.id] = character.name
        if character.player_name:
            self._player_name_index[character.player_name.lower()] = character.name
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.debug(f"✅ Character '{character.name}' added to campaign: '{self._current_campaign.name}'.")

    def _find_character(self, name_or_id_or_player: str) -> Character | None:
        """Find a character by name, ID, or player name using O(1) index lookup.

        Lookup priority:
        1. Character name (exact match)
        2. Character ID (8-char UUID)
        3. Player name (case-insensitive)
        """
        if not self._current_campaign:
            e = ValueError("❌ No active campaign! Wtf???")
            logger.error(e)
            raise e

        # Direct character name lookup - O(1)
        if name_or_id_or_player in self._current_campaign.characters:
            return self._current_campaign.characters[name_or_id_or_player]

        # ID lookup via index - O(1)
        if name_or_id_or_player in self._character_id_index:
            char_name = self._character_id_index[name_or_id_or_player]
            return self._current_campaign.characters.get(char_name)

        # Player name lookup (case-insensitive) - O(1)
        player_key = name_or_id_or_player.lower()
        if player_key in self._player_name_index:
            char_name = self._player_name_index[player_key]
            return self._current_campaign.characters.get(char_name)

        return None

    def get_character(self, name_or_id: str) -> Character | None:
        """Get a character by name or ID."""
        char = self._find_character(name_or_id)
        if not char:
            logger.error(f"❌ Character '{name_or_id}' not found!")
            return None
        logger.debug(f"✅ Found character '{char.name}'")
        return char

    def update_character(self, name_or_id: str, **kwargs) -> None:
        """Update a character's data."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.info(f"📝 Attempting to update character '{name_or_id}' with data: {kwargs}")
        character = self._find_character(name_or_id)
        if not character:
            e = ValueError(f"❌ Character '{name_or_id}' not found!")
            logger.error(e)
            raise e

        original_name = character.name
        original_player_name = character.player_name
        new_name = kwargs.get("name")
        new_player_name = kwargs.get("player_name")

        for key, value in kwargs.items():
            if hasattr(character, key):
                logger.debug(f"📝 Updating character '{original_name}': {key} -> {value}")
                setattr(character, key, value)

        character.updated_at = datetime.now()

        # Update character name in dict and indexes if changed
        if new_name and new_name != original_name:
            logger.debug(f"🏷️ Character name changed from '{original_name}' to '{new_name}'. Updating dictionary key.")
            self._current_campaign.characters[new_name] = self._current_campaign.characters.pop(original_name)
            self._character_id_index[character.id] = new_name
            # Update player name index to point to new character name
            if character.player_name:
                self._player_name_index[character.player_name.lower()] = new_name

        # Update player name index if player_name changed
        if new_player_name != original_player_name:
            # Remove old player name from index
            if original_player_name:
                self._player_name_index.pop(original_player_name.lower(), None)
            # Add new player name to index
            if new_player_name:
                char_name = new_name or original_name
                self._player_name_index[new_player_name.lower()] = char_name

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()
        logger.info(f"✅ Character '{new_name or original_name}' updated successfully.")

    def remove_character(self, name_or_id: str) -> None:
        """Remove a character from the campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        logger.debug(f"🗑️ Attempting to remove character '{name_or_id}'.")
        character_to_remove = self._find_character(name_or_id)
        if character_to_remove:
            char_name = character_to_remove.name
            char_id = character_to_remove.id
            player_name = character_to_remove.player_name
            logger.debug(f"🗑️ Found character '{char_name}' to remove.")
            # Remove from dict and all indexes
            del self._current_campaign.characters[char_name]
            self._character_id_index.pop(char_id, None)
            if player_name:
                self._player_name_index.pop(player_name.lower(), None)
            self._current_campaign.updated_at = datetime.now()
            self._save_campaign()
            logger.info(f"✅ Character '{char_name}' removed successfully.")
        else:
            logger.warning(f"⚠️ Character '{name_or_id}' not found for removal.")

    def list_characters(self) -> list[str]:
        """List all character names in the current campaign."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.characters.keys())

    def list_characters_detailed(self) -> list[Character]:
        """Return all characters without redundant lookups - O(n) instead of O(2n)."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.characters.values())

    # NPC Management
    def add_npc(self, npc: NPC) -> None:
        """Add an NPC to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.npcs[npc.name] = npc
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_npc(self, name: str) -> NPC | None:
        """Get an NPC by name."""
        if not self._current_campaign:
            return None
        return self._current_campaign.npcs.get(name)

    def list_npcs(self) -> list[str]:
        """List all NPC names."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.npcs.keys())

    def list_npcs_detailed(self) -> list[NPC]:
        """Return all NPCs without redundant lookups."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.npcs.values())

    # Location Management
    def add_location(self, location: Location) -> None:
        """Add a location to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.locations[location.name] = location
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_location(self, name: str) -> Location | None:
        """Get a location by name."""
        if not self._current_campaign:
            return None
        return self._current_campaign.locations.get(name)

    def list_locations(self) -> list[str]:
        """List all location names."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.locations.keys())

    def list_locations_detailed(self) -> list[Location]:
        """Return all locations without redundant lookups."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.locations.values())

    # Quest Management
    def add_quest(self, quest: Quest) -> None:
        """Add a quest to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.quests[quest.title] = quest
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_quest(self, title: str) -> Quest | None:
        """Get a quest by title."""
        if not self._current_campaign:
            return None
        return self._current_campaign.quests.get(title)

    def update_quest_status(self, title: str, status: str) -> None:
        """Update a quest's status."""
        quest = self.get_quest(title)
        if quest:
            quest.status = status
            self._current_campaign.updated_at = datetime.now()  # type: ignore
            self._save_campaign()

    def list_quests(self, status: str | None = None) -> list[str]:
        """List quest titles, optionally filtered by status."""
        if not self._current_campaign:
            return []

        quests = self._current_campaign.quests
        if status:
            return [title for title, quest in quests.items() if quest.status == status]
        return list(quests.keys())

    # Game State Management
    def update_game_state(self, **kwargs) -> None:
        """Update the game state."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        game_state = self._current_campaign.game_state
        for key, value in kwargs.items():
            if hasattr(game_state, key):
                setattr(game_state, key, value)

        game_state.updated_at = datetime.now()
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_game_state(self) -> GameState | None:
        """Get the current game state."""
        if not self._current_campaign:
            return None
        return self._current_campaign.game_state

    # Session Management
    def add_session_note(self, session_note: SessionNote) -> None:
        """Add a session note."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.sessions.append(session_note)
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_sessions(self) -> list[SessionNote]:
        """Get all session notes."""
        if not self._current_campaign:
            return []
        return self._current_campaign.sessions

    # Adventure Log / Events
    def add_event(self, event: AdventureEvent) -> None:
        """Add an event to the adventure log."""
        logger.info(f"➕ Adding event: '{event.title}' ({event.event_type})")
        self._events.append(event)
        self._save_events()
        logger.debug("✅ Event added and log saved.")

    def get_events(self, limit: int | None = None, event_type: str | None = None) -> list[AdventureEvent]:
        """Get adventure events, optionally filtered."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Sort by timestamp (newest first)
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        if limit:
            events = events[:limit]

        return events

    def search_events(self, query: str) -> list[AdventureEvent]:
        """Search events by title or description."""
        query_lower = query.lower()
        return [
            event for event in self._events
            if query_lower in event.title.lower() or query_lower in event.description.lower()
        ]


class SplitStorageBackend:
    """Storage backend that splits campaign data into separate JSON files.

    This backend stores campaign data in a directory structure with separate files
    for each data category (characters, npcs, locations, quests, encounters, game_state).
    Sessions are stored in individual files in a subdirectory.

    Directory structure:
        data/campaigns/{campaign-name}/
        ├── campaign.json      # Metadata only
        ├── characters.json
        ├── npcs.json
        ├── locations.json
        ├── quests.json
        ├── encounters.json
        ├── game_state.json
        └── sessions/
            └── session-{NNN}.json

    Features:
    - Per-file dirty tracking using SHA-256 hashes
    - Only writes files that have been modified
    - Atomic writes (write to temp file, then rename)
    """

    def __init__(self, data_dir: str | Path = "dnd_data", auto_load: bool = True):
        """Initialize split storage backend.

        Args:
            data_dir: Base directory for all campaign data
            auto_load: If True, automatically load the most recent campaign
        """
        self.data_dir = Path(data_dir)
        logger.debug(f"📂 Initializing SplitStorageBackend with data_dir: {self.data_dir.resolve()}")
        self.data_dir.mkdir(exist_ok=True)

        # Create campaigns subdirectory
        (self.data_dir / "campaigns").mkdir(exist_ok=True)
        logger.debug("📂 Storage subdirectories ensured.")

        self._current_campaign: Campaign | None = None

        # Per-section hash tracking for dirty detection
        self._section_hashes: dict[str, str] = {
            "campaign": "",
            "characters": "",
            "npcs": "",
            "locations": "",
            "quests": "",
            "encounters": "",
            "game_state": "",
        }

        # Load existing data if auto_load is enabled
        if auto_load:
            logger.debug("📂 Loading initial data...")
            self._load_current_campaign()
            logger.debug("✅ Initial data loaded.")

    def _get_campaign_dir(self, campaign_name: str | None = None) -> Path:
        """Get the directory path for a campaign.

        Args:
            campaign_name: Name of the campaign. Uses current campaign if None.

        Returns:
            Path to campaign directory

        Raises:
            ValueError: If no campaign name provided and no current campaign
        """
        if campaign_name is None and self._current_campaign:
            campaign_name = self._current_campaign.name
        if campaign_name is None:
            raise ValueError("No campaign name provided and no current campaign")

        safe_name = "".join(c for c in campaign_name if c.isalnum() or c in (' ', '-', '_', "'")).rstrip()
        return self.data_dir / "campaigns" / safe_name

    def _ensure_campaign_structure(self, campaign_name: str) -> None:
        """Create the directory structure for a campaign.

        Args:
            campaign_name: Name of the campaign
        """
        campaign_dir = self._get_campaign_dir(campaign_name)
        campaign_dir.mkdir(parents=True, exist_ok=True)
        (campaign_dir / "sessions").mkdir(exist_ok=True)
        logger.debug(f"✅ Ensured directory structure for campaign '{campaign_name}'")

    def _compute_section_hash(self, data: dict | list) -> str:
        """Compute SHA-256 hash of a data section for dirty tracking.

        Args:
            data: Data to hash (dict or list)

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
        temp_file = file_path.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            temp_file.replace(file_path)
            logger.debug(f"✅ Atomic write to {file_path.name} successful")
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            logger.error(f"❌ Error during atomic write to {file_path.name}: {e}")
            raise

    def _save_characters(self, force: bool = False) -> None:
        """Save characters to characters.json if modified.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        characters_data = {
            name: char.model_dump(mode='json')
            for name, char in self._current_campaign.characters.items()
        }

        current_hash = self._compute_section_hash(characters_data)
        if not force and current_hash == self._section_hashes["characters"]:
            logger.debug("✅ Characters unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "characters.json"
        self._atomic_write(file_path, characters_data)
        self._section_hashes["characters"] = current_hash
        logger.debug(f"💾 Saved characters to {file_path}")

    def _save_npcs(self, force: bool = False) -> None:
        """Save NPCs to npcs.json if modified.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        npcs_data = {
            name: npc.model_dump(mode='json')
            for name, npc in self._current_campaign.npcs.items()
        }

        current_hash = self._compute_section_hash(npcs_data)
        if not force and current_hash == self._section_hashes["npcs"]:
            logger.debug("✅ NPCs unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "npcs.json"
        self._atomic_write(file_path, npcs_data)
        self._section_hashes["npcs"] = current_hash
        logger.debug(f"💾 Saved NPCs to {file_path}")

    def _save_locations(self, force: bool = False) -> None:
        """Save locations to locations.json if modified.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        locations_data = {
            name: loc.model_dump(mode='json')
            for name, loc in self._current_campaign.locations.items()
        }

        current_hash = self._compute_section_hash(locations_data)
        if not force and current_hash == self._section_hashes["locations"]:
            logger.debug("✅ Locations unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "locations.json"
        self._atomic_write(file_path, locations_data)
        self._section_hashes["locations"] = current_hash
        logger.debug(f"💾 Saved locations to {file_path}")

    def _save_quests(self, force: bool = False) -> None:
        """Save quests to quests.json if modified.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        quests_data = {
            title: quest.model_dump(mode='json')
            for title, quest in self._current_campaign.quests.items()
        }

        current_hash = self._compute_section_hash(quests_data)
        if not force and current_hash == self._section_hashes["quests"]:
            logger.debug("✅ Quests unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "quests.json"
        self._atomic_write(file_path, quests_data)
        self._section_hashes["quests"] = current_hash
        logger.debug(f"💾 Saved quests to {file_path}")

    def _save_encounters(self, force: bool = False) -> None:
        """Save encounters to encounters.json if modified.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        encounters_data = {
            name: enc.model_dump(mode='json')
            for name, enc in self._current_campaign.encounters.items()
        }

        current_hash = self._compute_section_hash(encounters_data)
        if not force and current_hash == self._section_hashes["encounters"]:
            logger.debug("✅ Encounters unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "encounters.json"
        self._atomic_write(file_path, encounters_data)
        self._section_hashes["encounters"] = current_hash
        logger.debug(f"💾 Saved encounters to {file_path}")

    def _save_game_state(self, force: bool = False) -> None:
        """Save game state to game_state.json if modified.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        game_state_data = self._current_campaign.game_state.model_dump(mode='json')

        current_hash = self._compute_section_hash(game_state_data)
        if not force and current_hash == self._section_hashes["game_state"]:
            logger.debug("✅ Game state unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "game_state.json"
        self._atomic_write(file_path, game_state_data)
        self._section_hashes["game_state"] = current_hash
        logger.debug(f"💾 Saved game state to {file_path}")

    def _save_campaign_metadata(self, force: bool = False) -> None:
        """Save campaign metadata to campaign.json if modified.

        Only saves core metadata fields (id, name, description, dm_name, setting,
        world_notes, created_at, updated_at). Data fields are stored in separate files.

        Args:
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        # Extract only metadata fields
        metadata = {
            "id": self._current_campaign.id,
            "name": self._current_campaign.name,
            "description": self._current_campaign.description,
            "dm_name": self._current_campaign.dm_name,
            "setting": str(self._current_campaign.setting) if self._current_campaign.setting else None,
            "world_notes": self._current_campaign.world_notes,
            "created_at": self._current_campaign.created_at.isoformat(),
            "updated_at": self._current_campaign.updated_at.isoformat() if self._current_campaign.updated_at else None,
        }

        current_hash = self._compute_section_hash(metadata)
        if not force and current_hash == self._section_hashes["campaign"]:
            logger.debug("✅ Campaign metadata unchanged, skipping save.")
            return

        campaign_dir = self._get_campaign_dir()
        file_path = campaign_dir / "campaign.json"
        self._atomic_write(file_path, metadata)
        self._section_hashes["campaign"] = current_hash
        logger.debug(f"💾 Saved campaign metadata to {file_path}")

    def _save_session(self, session: SessionNote, force: bool = False) -> None:
        """Save a session note to sessions/session-{NNN}.json.

        Args:
            session: Session note to save
            force: If True, save even if unchanged
        """
        if not self._current_campaign:
            return

        campaign_dir = self._get_campaign_dir()
        sessions_dir = campaign_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)

        file_path = sessions_dir / f"session-{session.session_number:03d}.json"
        session_data = session.model_dump(mode='json')

        # Check if file exists and compare hash
        if not force and file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                existing_hash = self._compute_section_hash(existing_data)
                current_hash = self._compute_section_hash(session_data)
                if existing_hash == current_hash:
                    logger.debug(f"✅ Session {session.session_number} unchanged, skipping save.")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Error reading existing session file: {e}")

        self._atomic_write(file_path, session_data)
        logger.debug(f"💾 Saved session {session.session_number} to {file_path}")

    def save_all(self, force: bool = False) -> None:
        """Save all campaign data to their respective files.

        Args:
            force: If True, save all files regardless of dirty state
        """
        if not self._current_campaign:
            logger.debug("❌ No current campaign to save.")
            return

        logger.info(f"💾 Saving campaign '{self._current_campaign.name}'")

        # Save metadata first
        self._save_campaign_metadata(force=force)

        # Save all data sections
        self._save_characters(force=force)
        self._save_npcs(force=force)
        self._save_locations(force=force)
        self._save_quests(force=force)
        self._save_encounters(force=force)
        self._save_game_state(force=force)

        # Save all sessions
        for session in self._current_campaign.sessions:
            self._save_session(session, force=force)

        logger.info(f"✅ Campaign '{self._current_campaign.name}' saved successfully.")

    def _load_characters(self, campaign_dir: Path) -> dict[str, Character]:
        """Load characters from characters.json.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Dictionary of character name to Character object
        """
        file_path = campaign_dir / "characters.json"
        if not file_path.exists():
            logger.debug("No characters.json found, returning empty dict.")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            characters = {
                name: Character.model_validate(char_data)
                for name, char_data in data.items()
            }
            self._section_hashes["characters"] = self._compute_section_hash(data)
            logger.debug(f"✅ Loaded {len(characters)} characters")
            return characters
        except Exception as e:
            logger.error(f"❌ Error loading characters: {e}")
            return {}

    def _load_npcs(self, campaign_dir: Path) -> dict[str, NPC]:
        """Load NPCs from npcs.json.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Dictionary of NPC name to NPC object
        """
        file_path = campaign_dir / "npcs.json"
        if not file_path.exists():
            logger.debug("No npcs.json found, returning empty dict.")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            npcs = {
                name: NPC.model_validate(npc_data)
                for name, npc_data in data.items()
            }
            self._section_hashes["npcs"] = self._compute_section_hash(data)
            logger.debug(f"✅ Loaded {len(npcs)} NPCs")
            return npcs
        except Exception as e:
            logger.error(f"❌ Error loading NPCs: {e}")
            return {}

    def _load_locations(self, campaign_dir: Path) -> dict[str, Location]:
        """Load locations from locations.json.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Dictionary of location name to Location object
        """
        file_path = campaign_dir / "locations.json"
        if not file_path.exists():
            logger.debug("No locations.json found, returning empty dict.")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            locations = {
                name: Location.model_validate(loc_data)
                for name, loc_data in data.items()
            }
            self._section_hashes["locations"] = self._compute_section_hash(data)
            logger.debug(f"✅ Loaded {len(locations)} locations")
            return locations
        except Exception as e:
            logger.error(f"❌ Error loading locations: {e}")
            return {}

    def _load_quests(self, campaign_dir: Path) -> dict[str, Quest]:
        """Load quests from quests.json.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Dictionary of quest title to Quest object
        """
        file_path = campaign_dir / "quests.json"
        if not file_path.exists():
            logger.debug("No quests.json found, returning empty dict.")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            quests = {
                title: Quest.model_validate(quest_data)
                for title, quest_data in data.items()
            }
            self._section_hashes["quests"] = self._compute_section_hash(data)
            logger.debug(f"✅ Loaded {len(quests)} quests")
            return quests
        except Exception as e:
            logger.error(f"❌ Error loading quests: {e}")
            return {}

    def _load_encounters(self, campaign_dir: Path) -> dict[str, CombatEncounter]:
        """Load encounters from encounters.json.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Dictionary of encounter name to CombatEncounter object
        """
        file_path = campaign_dir / "encounters.json"
        if not file_path.exists():
            logger.debug("No encounters.json found, returning empty dict.")
            return {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            encounters = {
                name: CombatEncounter.model_validate(enc_data)
                for name, enc_data in data.items()
            }
            self._section_hashes["encounters"] = self._compute_section_hash(data)
            logger.debug(f"✅ Loaded {len(encounters)} encounters")
            return encounters
        except Exception as e:
            logger.error(f"❌ Error loading encounters: {e}")
            return {}

    def _load_game_state(self, campaign_dir: Path, campaign_name: str) -> GameState:
        """Load game state from game_state.json.

        Args:
            campaign_dir: Path to campaign directory
            campaign_name: Name of the campaign (for default GameState)

        Returns:
            GameState object
        """
        file_path = campaign_dir / "game_state.json"
        if not file_path.exists():
            logger.debug("No game_state.json found, creating default.")
            return GameState(campaign_name=campaign_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            game_state = GameState.model_validate(data)
            self._section_hashes["game_state"] = self._compute_section_hash(data)
            logger.debug("✅ Loaded game state")
            return game_state
        except Exception as e:
            logger.error(f"❌ Error loading game state: {e}")
            return GameState(campaign_name=campaign_name)

    def _load_sessions(self, campaign_dir: Path) -> list[SessionNote]:
        """Load session notes from sessions/ subdirectory.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            List of SessionNote objects, sorted by session number
        """
        sessions_dir = campaign_dir / "sessions"
        if not sessions_dir.exists():
            logger.debug("No sessions directory found, returning empty list.")
            return []

        sessions = []
        session_files = sorted(sessions_dir.glob("session-*.json"))

        for file_path in session_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                session = SessionNote.model_validate(data)
                sessions.append(session)
            except Exception as e:
                logger.error(f"❌ Error loading session from {file_path.name}: {e}")

        logger.debug(f"✅ Loaded {len(sessions)} sessions")
        return sorted(sessions, key=lambda s: s.session_number)

    def _load_campaign_metadata(self, campaign_dir: Path) -> dict:
        """Load campaign metadata from campaign.json.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Dictionary with campaign metadata

        Raises:
            FileNotFoundError: If campaign.json does not exist
        """
        file_path = campaign_dir / "campaign.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Campaign metadata file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._section_hashes["campaign"] = self._compute_section_hash(data)
        logger.debug("✅ Loaded campaign metadata")
        return data

    def _load_current_campaign(self) -> None:
        """Load the most recently modified campaign."""
        logger.debug("📂 Attempting to load the most recent campaign...")
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            logger.debug("❌ Campaigns directory does not exist. No campaign loaded.")
            return

        # Find the most recent campaign directory
        campaign_dirs = [d for d in campaigns_dir.iterdir() if d.is_dir()]
        if not campaign_dirs:
            logger.debug("❌ No campaign directories found.")
            return

        # Sort by modification time and load the most recent
        latest_dir = max(campaign_dirs, key=lambda d: d.stat().st_mtime)
        logger.debug(f"📂 Most recent campaign directory is '{latest_dir.name}'.")

        try:
            self._load_campaign_from_dir(latest_dir)
            logger.info(f"✅ Successfully loaded campaign: {self._current_campaign.name}")  # type: ignore
        except Exception as e:
            logger.error(f"❌ Error loading campaign from {latest_dir.name}: {e}")

    def _load_campaign_from_dir(self, campaign_dir: Path) -> Campaign:
        """Load a campaign from a directory.

        Args:
            campaign_dir: Path to campaign directory

        Returns:
            Campaign object

        Raises:
            FileNotFoundError: If campaign.json does not exist
        """
        metadata = self._load_campaign_metadata(campaign_dir)

        # Load all data sections
        characters = self._load_characters(campaign_dir)
        npcs = self._load_npcs(campaign_dir)
        locations = self._load_locations(campaign_dir)
        quests = self._load_quests(campaign_dir)
        encounters = self._load_encounters(campaign_dir)
        game_state = self._load_game_state(campaign_dir, metadata["name"])
        sessions = self._load_sessions(campaign_dir)

        # Construct Campaign object
        campaign = Campaign(
            id=metadata.get("id", new_uuid()),
            name=metadata["name"],
            description=metadata["description"],
            dm_name=metadata.get("dm_name"),
            setting=metadata.get("setting"),
            characters=characters,
            npcs=npcs,
            locations=locations,
            quests=quests,
            encounters=encounters,
            sessions=sessions,
            game_state=game_state,
            world_notes=metadata.get("world_notes", ""),
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]) if metadata.get("updated_at") else None,
        )

        self._current_campaign = campaign
        return campaign

    def create_campaign(self, name: str, description: str, dm_name: str | None = None, setting: str | Path | None = None) -> Campaign:
        """Create a new campaign.

        Args:
            name: Campaign name
            description: Campaign description
            dm_name: Dungeon Master name
            setting: Campaign setting (string or path to file)

        Returns:
            New Campaign object
        """
        logger.info(f"✨ Creating new campaign: '{name}'")

        # Ensure directory structure exists
        self._ensure_campaign_structure(name)

        # Create campaign object
        game_state = GameState(campaign_name=name)
        campaign = Campaign(
            name=name,
            description=description,
            dm_name=dm_name,
            setting=setting,
            game_state=game_state
        )

        self._current_campaign = campaign
        self.save_all(force=True)  # Force save for new campaign
        logger.info(f"✅ Campaign '{name}' created and set as active.")
        return campaign

    def get_current_campaign(self) -> Campaign | None:
        """Get the current campaign.

        Returns:
            Current Campaign object or None
        """
        return self._current_campaign

    def list_campaigns(self) -> list[str]:
        """List all available campaigns.

        Returns:
            List of campaign names
        """
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            return []

        return [d.name for d in campaigns_dir.iterdir() if d.is_dir()]

    def load_campaign(self, name: str) -> Campaign:
        """Load a specific campaign.

        Args:
            name: Campaign name to load

        Returns:
            Loaded Campaign object

        Raises:
            FileNotFoundError: If campaign does not exist
        """
        logger.info(f"📂 Attempting to load campaign: '{name}'")
        campaign_dir = self._get_campaign_dir(name)
        logger.debug(f"📂 Campaign directory path: {campaign_dir}")

        if not campaign_dir.exists():
            logger.error(f"❌ Campaign directory not found for '{name}'")
            raise FileNotFoundError(f"Campaign '{name}' not found")

        campaign = self._load_campaign_from_dir(campaign_dir)
        logger.info(f"✅ Successfully loaded campaign '{name}'.")
        return campaign
