"""
Data models for the D&D MCP Server.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
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
    hit_dice: str  # e.g., "1d8"
    subclass: Optional[str] = None


class Race(BaseModel):
    """Character race information."""
    name: str
    subrace: Optional[str] = None
    traits: List[str] = Field(default_factory=list)


class Item(BaseModel):
    """Generic item model."""
    name: str
    description: Optional[str] = None
    quantity: int = 1
    weight: Optional[float] = None
    value: Optional[str] = None  # e.g., "50 gp"
    item_type: str = "misc"  # weapon, armor, consumable, misc, etc.
    properties: Dict[str, Any] = Field(default_factory=dict)


class Spell(BaseModel):
    """Spell information."""
    name: str
    level: int = Field(ge=0, le=9)
    school: str
    casting_time: str
    range: str
    duration: str
    components: List[str]  # V, S, M
    description: str
    material_components: Optional[str] = None
    prepared: bool = False


class Character(BaseModel):
    """Complete character sheet."""
    # Basic Info
    name: str
    player_name: Optional[str] = None
    character_class: CharacterClass
    race: Race
    background: Optional[str] = None
    alignment: Optional[str] = None
    
    # Core Stats
    abilities: Dict[str, AbilityScore] = Field(
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
    skill_proficiencies: List[str] = Field(default_factory=list)
    saving_throw_proficiencies: List[str] = Field(default_factory=list)
    
    # Equipment
    inventory: List[Item] = Field(default_factory=list)
    equipment: Dict[str, Optional[Item]] = Field(
        default_factory=lambda: {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "shield": None,
        }
    )
    
    # Spellcasting
    spellcasting_ability: Optional[str] = None
    spell_slots: Dict[int, int] = Field(default_factory=dict)  # level: max_slots
    spell_slots_used: Dict[int, int] = Field(default_factory=dict)  # level: used_slots
    spells_known: List[Spell] = Field(default_factory=list)
    
    # Character Features
    features_and_traits: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    
    # Misc
    inspiration: bool = False
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NPC(BaseModel):
    """Non-player character."""
    name: str
    description: Optional[str] = None
    race: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    attitude: Optional[str] = None  # friendly, neutral, hostile, etc.
    notes: str = ""
    stats: Optional[Dict[str, Any]] = None  # Combat stats if needed
    relationships: Dict[str, str] = Field(default_factory=dict)  # character_name: relationship


class Location(BaseModel):
    """Geographic location or settlement."""
    name: str
    location_type: str  # city, town, village, dungeon, forest, etc.
    description: str
    population: Optional[int] = None
    government: Optional[str] = None
    notable_features: List[str] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)  # NPC names
    connections: List[str] = Field(default_factory=list)  # Connected locations
    notes: str = ""


class Quest(BaseModel):
    """Quest or mission."""
    title: str
    description: str
    giver: Optional[str] = None  # NPC who gave the quest
    status: str = "active"  # active, completed, failed, on_hold
    objectives: List[str] = Field(default_factory=list)
    completed_objectives: List[str] = Field(default_factory=list)
    reward: Optional[str] = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class CombatEncounter(BaseModel):
    """Combat encounter details."""
    name: str
    description: str
    enemies: List[str] = Field(default_factory=list)
    difficulty: Optional[str] = None  # easy, medium, hard, deadly
    experience_value: Optional[int] = None
    location: Optional[str] = None
    status: str = "planned"  # planned, active, completed
    notes: str = ""


class SessionNote(BaseModel):
    """Session notes and summary."""
    session_number: int
    date: datetime = Field(default_factory=datetime.now)
    title: Optional[str] = None
    summary: str
    events: List[str] = Field(default_factory=list)
    characters_present: List[str] = Field(default_factory=list)
    experience_gained: Optional[int] = None
    treasure_found: List[str] = Field(default_factory=list)
    notes: str = ""


class GameState(BaseModel):
    """Current state of the game."""
    campaign_name: str
    current_session: int = 1
    current_date_in_game: Optional[str] = None
    current_location: Optional[str] = None
    active_quests: List[str] = Field(default_factory=list)
    party_level: int = 1
    party_funds: str = "0 gp"
    initiative_order: List[Dict[str, Any]] = Field(default_factory=list)
    in_combat: bool = False
    current_turn: Optional[str] = None
    notes: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)


class Campaign(BaseModel):
    """Main campaign container."""
    name: str
    description: str
    dm_name: Optional[str] = None
    setting: Optional[str] = None
    characters: Dict[str, Character] = Field(default_factory=dict)
    npcs: Dict[str, NPC] = Field(default_factory=dict)
    locations: Dict[str, Location] = Field(default_factory=dict)
    quests: Dict[str, Quest] = Field(default_factory=dict)
    encounters: Dict[str, CombatEncounter] = Field(default_factory=dict)
    sessions: List[SessionNote] = Field(default_factory=list)
    game_state: GameState
    world_notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


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
    session_number: Optional[int] = None
    characters_involved: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    importance: int = Field(ge=1, le=5, default=3)  # 1=minor, 5=major
