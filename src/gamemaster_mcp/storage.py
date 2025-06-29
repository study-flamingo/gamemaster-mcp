"""
Storage layer for the D&D MCP Server.
Handles persistence of campaign data to JSON files.
"""

import logging

import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from .models import (
    Campaign, Character, NPC, Location, Quest, CombatEncounter,
    SessionNote, GameState, AdventureEvent
)

logger = logging.getLogger("gamemaster-mcp")

if not load_dotenv():
    logger.warning(".env file not found! Please see the README.md for instructions. Using project root instead.")

data_path = Path(os.getenv("GAMEMASTER_STORAGE_DIR", "./")).resolve()
logger.info(f"Data path: {data_path}")

class DnDStorage:
    """Handles storage and retrieval of D&D campaign data."""

    def __init__(self, data_dir: str = "dnd_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.data_dir / "campaigns").mkdir(exist_ok=True)
        (self.data_dir / "events").mkdir(exist_ok=True)

        self._current_campaign: Campaign | None = None
        self._events: list[AdventureEvent] = []

        # Load existing data
        self._load_current_campaign()
        self._load_events()

    def _get_campaign_file(self, campaign_name: str | None = None) -> Path:
        """Get the file path for a campaign."""
        if campaign_name is None and self._current_campaign:
            campaign_name = self._current_campaign.name
        if campaign_name is None:
            raise ValueError("No campaign name provided and no current campaign")

        safe_name = "".join(c for c in campaign_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return self.data_dir / "campaigns" / f"{safe_name}.json"

    def _get_events_file(self) -> Path:
        """Get the file path for adventure events."""
        return self.data_dir / "events" / "adventure_log.json"

    def _save_campaign(self):
        """Save the current campaign to disk."""
        if not self._current_campaign:
            return

        campaign_file = self._get_campaign_file()
        campaign_data = self._current_campaign.model_dump(mode='json')

        with open(campaign_file, 'w', encoding='utf-8') as f:
            json.dump(campaign_data, f, indent=2, default=str)

    def _load_current_campaign(self):
        """Load the most recently used campaign."""
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            return

        # Find the most recent campaign file
        campaign_files = list(campaigns_dir.glob("*.json"))
        if not campaign_files:
            return

        # Sort by modification time and load the most recent
        latest_file = max(campaign_files, key=lambda f: f.stat().st_mtime)

        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._current_campaign = Campaign.model_validate(data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading campaign from {latest_file}: {e}")

    def _save_events(self):
        """Save adventure events to disk."""
        events_file = self._get_events_file()
        events_data = [event.model_dump(mode='json') for event in self._events]

        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, default=str)

    def _load_events(self):
        """Load adventure events from disk."""
        events_file = self._get_events_file()
        if not events_file.exists():
            return

        try:
            with open(events_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
            self._events = [AdventureEvent.model_validate(event) for event in events_data]
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading events: {e}")

    # Campaign Management
    def create_campaign(self, name: str, description: str, dm_name: str | None = None, setting: str | None = None) -> Campaign:
        """Create a new campaign."""
        game_state = GameState(campaign_name=name)

        campaign = Campaign(
            name=name,
            description=description,
            dm_name=dm_name,
            setting=setting,
            game_state=game_state
        )

        self._current_campaign = campaign
        self._save_campaign()
        return campaign

    def get_current_campaign(self) -> Campaign | None:
        """Get the current campaign."""
        return self._current_campaign

    def list_campaigns(self) -> list[str]:
        """List all available campaigns."""
        campaigns_dir = self.data_dir / "campaigns"
        if not campaigns_dir.exists():
            return []

        return [f.stem for f in campaigns_dir.glob("*.json")]

    def load_campaign(self, name: str) -> Campaign:
        """Load a specific campaign."""
        campaign_file = self._get_campaign_file(name)

        if not campaign_file.exists():
            raise FileNotFoundError(f"Campaign '{name}' not found")

        with open(campaign_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._current_campaign = Campaign.model_validate(data)
        return self._current_campaign

    def update_campaign(self, **kwargs):
        """Update campaign metadata."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        for key, value in kwargs.items():
            if hasattr(self._current_campaign, key):
                setattr(self._current_campaign, key, value)

        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    # Character Management
    def add_character(self, character: Character) -> None:
        """Add a character to the current campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        self._current_campaign.characters[character.name] = character
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def get_character(self, name: str) -> Character | None:
        """Get a character by name."""
        if not self._current_campaign:
            return None
        return self._current_campaign.characters.get(name)

    def update_character(self, name: str, **kwargs) -> None:
        """Update a character's data."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        character = self._current_campaign.characters.get(name)
        if not character:
            raise ValueError(f"Character '{name}' not found")

        for key, value in kwargs.items():
            if hasattr(character, key):
                setattr(character, key, value)

        character.updated_at = datetime.now()
        self._current_campaign.updated_at = datetime.now()
        self._save_campaign()

    def remove_character(self, name: str) -> None:
        """Remove a character from the campaign."""
        if not self._current_campaign:
            raise ValueError("No current campaign")

        if name in self._current_campaign.characters:
            del self._current_campaign.characters[name]
            self._current_campaign.updated_at = datetime.now()
            self._save_campaign()

    def list_characters(self) -> list[str]:
        """List all character names in the current campaign."""
        if not self._current_campaign:
            return []
        return list(self._current_campaign.characters.keys())

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
            self._current_campaign.updated_at = datetime.now()
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
        self._events.append(event)
        self._save_events()

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
