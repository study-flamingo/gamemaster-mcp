"""
Data models for the D&D MCP Server.
"""

from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Any, Annotated
from pydantic import BaseModel, Field


class AbilityScore(BaseModel):
    """D&D ability score with modifiers."""
    score: int = Field(ge=1, le=30, description="Raw ability score")

    @property
    def modifier(self) -> int:
        """Calculate ability modifier."""
        return (self.score - 10) // 2


class CharacterClass(BaseModel):
    """Character class information."""
    name: str
    level: int = Field(ge=1, le=20)
    hit_dice: Annotated[str, "The type of hit dice for this character. E.g.. '1d8'"] = "1d4" # e.g., "1d8"
    subclass: Annotated[str | None, "The character's subclass."] = None


class Race(BaseModel):
    """Character race information."""
    name: str
    subrace: str | None = None
    traits: list[str] = Field(default_factory=list)


class Item(BaseModel):
    """Generic item model."""
    name: str
    description: str | None = None
    quantity: int = 1
    weight: float | None = None
    value: str | None = None  # e.g., "50 gp"
    item_type: str = "misc"  # weapon, armor, consumable, misc, etc.
    properties: dict[str, Any] = Field(default_factory=dict)


class Spell(BaseModel):
    """Spell information."""
    name: str
    level: int = Field(ge=0, le=9)
    school: str
    casting_time: str
    range: str
    duration: str
    components: list[str]  # V, S, M
    description: str
    material_components: str | None = None
    prepared: bool = False


class Character(BaseModel):
    """Complete character sheet."""
    # Basic Info
    name: str
    player_name: str | None = None
    character_class: CharacterClass
    race: Race
    background: str | None = None
    alignment: str | None = None

    # Core Stats
    abilities: dict[str, AbilityScore] = Field(
        default_factory=lambda: {
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=10),
            "constitution": AbilityScore(score=10),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=10),
            "charisma": AbilityScore(score=10),
        }
    )

    # Combat Stats
    armor_class: int = 10
    hit_points_max: int = 1
    hit_points_current: int = 1
    temporary_hit_points: int = 0
    hit_dice_remaining: str = "1d8"
    death_saves_success: int = Field(ge=0, le=3, default=0)
    death_saves_failure: int = Field(ge=0, le=3, default=0)

    # Skills & Proficiencies
    proficiency_bonus: int = 2
    skill_proficiencies: list[str] = Field(default_factory=list)
    saving_throw_proficiencies: list[str] = Field(default_factory=list)

    # Equipment
    inventory: list[Item] = Field(default_factory=list)
    equipment: dict[str, Item | None] = Field(
        default_factory=lambda: {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "shield": None,
        }
    )

    # Spellcasting
    spellcasting_ability: str | None = None
    spell_slots: dict[int, int] = Field(default_factory=dict)  # level: max_slots
    spell_slots_used: dict[int, int] = Field(default_factory=dict)  # level: used_slots
    spells_known: list[Spell] = Field(default_factory=list)

    # Character Features
    features_and_traits: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    # Misc
    inspiration: bool = False
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NPC(BaseModel):
    """Non-player character."""
    name: str
    description: str | None = None
    race: str | None = None
    occupation: str | None = None
    location: str | None = None
    attitude: str | None = None  # friendly, neutral, hostile, etc.
    notes: str = ""
    stats: dict[str, Any] | None = None  # Combat stats if needed
    relationships: dict[str, str] = Field(default_factory=dict)  # character_name: relationship


class Location(BaseModel):
    """Geographic location or settlement."""
    name: str
    location_type: str  # city, town, village, dungeon, forest, etc.
    description: str
    population: int | None = None
    government: str | None = None
    notable_features: list[str] = Field(default_factory=list)
    npcs: list[str] = Field(default_factory=list)  # NPC names
    connections: list[str] = Field(default_factory=list)  # Connected locations
    notes: str = ""


class Quest(BaseModel):
    """Quest or mission."""
    title: str
    description: str
    giver: str | None = None  # NPC who gave the quest
    status: str = "active"  # active, completed, failed, on_hold
    objectives: list[str] = Field(default_factory=list)
    completed_objectives: list[str] = Field(default_factory=list)
    reward: str | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class CombatEncounter(BaseModel):
    """Combat encounter details."""
    name: str
    description: str
    enemies: list[str] = Field(default_factory=list)
    difficulty: str | None = None  # easy, medium, hard, deadly
    experience_value: int | None = None
    location: str | None = None
    status: str = "planned"  # planned, active, completed
    notes: str = ""


class SessionNote(BaseModel):
    """Session notes and summary."""
    session_number: int
    date: datetime = Field(default_factory=datetime.now)
    title: str | None = None
    summary: str
    events: list[str] = Field(default_factory=list)
    characters_present: list[str] = Field(default_factory=list)
    experience_gained: int | None = None
    treasure_found: list[str] = Field(default_factory=list)
    notes: str = ""


class GameState(BaseModel):
    """Current state of the game."""
    campaign_name: str
    current_session: int = 1
    current_date_in_game: str | None = None
    current_location: str | None = None
    active_quests: list[str] = Field(default_factory=list)
    party_level: int = 1
    party_funds: str = "0 gp"
    initiative_order: list[dict[str, Any]] = Field(default_factory=list)
    in_combat: bool = False
    current_turn: str | None = None
    notes: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


class Campaign(BaseModel):
    """Main campaign container."""
    name: str
    description: str
    dm_name: str | None = None
    setting: str | Path | None = None
    characters: dict[str, Character] = Field(default_factory=dict)
    npcs: dict[str, NPC] = Field(default_factory=dict)
    locations: dict[str, Location] = Field(default_factory=dict)
    quests: dict[str, Quest] = Field(default_factory=dict)
    encounters: dict[str, CombatEncounter] = Field(default_factory=dict)
    sessions: list[SessionNote] = Field(default_factory=list)
    game_state: GameState
    world_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = Field(default_factory=datetime.now)


# Event types for the adventure log
class EventType(str, Enum):
    COMBAT = "combat"
    ROLEPLAY = "roleplay"
    EXPLORATION = "exploration"
    QUEST = "quest"
    CHARACTER = "character"
    WORLD = "world"
    SESSION = "session"


class AdventureEvent(BaseModel):
    """Individual event in the adventure log."""
    event_type: EventType
    title: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.now)
    session_number: int | None = None
    characters_involved: list[str] = Field(default_factory=list)
    location: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: int = Field(ge=1, le=5, default=3)  # 1=minor, 5=major

__all__ = [
    "AbilityScore",
    "CharacterClass",
    "Race",
    "Item",
    "Spell",
    "Character",
    "NPC",
    "Location",
    "Quest",
    "CombatEncounter",
    "SessionNote",
    "GameState",
    "Campaign",
    "EventType",
    "AdventureEvent",
]