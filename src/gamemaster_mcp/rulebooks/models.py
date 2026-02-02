"""
Data models for rulebook content.

These models represent structured data from SRD, Open5e, and custom rulebooks.
They are designed to capture all SRD data while remaining extensible for homebrew.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Enums and Constants
# =============================================================================

class RulebookSource(str, Enum):
    """Source type for rulebook content."""
    SRD = "srd"
    OPEN5E = "open5e"
    CUSTOM = "custom"


class Size(str, Enum):
    """Creature/character size categories."""
    TINY = "Tiny"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    HUGE = "Huge"
    GARGANTUAN = "Gargantuan"


class SpellSchool(str, Enum):
    """Schools of magic."""
    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"


class ItemRarity(str, Enum):
    """Magic item rarity levels."""
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"
    VERY_RARE = "Very Rare"
    LEGENDARY = "Legendary"
    ARTIFACT = "Artifact"


# =============================================================================
# Base Models
# =============================================================================

class RulebookEntry(BaseModel):
    """Base class for all rulebook content entries."""
    index: str = Field(description="Unique identifier, typically lowercase with hyphens")
    name: str = Field(description="Display name")
    source: str = Field(default="srd", description="Source identifier (srd, open5e, or custom rulebook name)")
    url: str | None = Field(default=None, description="API URL if from external source")


# =============================================================================
# Spellcasting Models
# =============================================================================

class SpellcastingInfo(BaseModel):
    """Spellcasting information for a class."""
    level: int = Field(ge=1, description="Level at which spellcasting is gained")
    spellcasting_ability: str = Field(description="Ability used for spellcasting (e.g., 'INT', 'WIS', 'CHA')")
    caster_type: Literal["full", "half", "third", "pact"] = Field(
        default="full",
        description="Caster progression type"
    )
    cantrips_known: list[int] | None = Field(
        default=None,
        description="Cantrips known by level (index 0 = level 1)"
    )
    spells_known: list[int] | None = Field(
        default=None,
        description="Spells known by level (for known casters like Sorcerer)"
    )
    spell_slots: dict[int, list[int]] | None = Field(
        default=None,
        description="Spell slots per level. Key = character level, Value = [1st, 2nd, 3rd, ...]"
    )


class ClassLevelInfo(BaseModel):
    """Features and bonuses gained at a specific class level."""
    level: int = Field(ge=1, le=20)
    proficiency_bonus: int = Field(ge=2, le=6)
    features: list[str] = Field(default_factory=list, description="Feature names gained at this level")
    feature_details: dict[str, str] = Field(
        default_factory=dict,
        description="Feature name -> description"
    )
    class_specific: dict[str, Any] = Field(
        default_factory=dict,
        description="Class-specific values (e.g., Rage Damage for Barbarian, Sneak Attack dice for Rogue)"
    )


# =============================================================================
# Class Models
# =============================================================================

class SubclassDefinition(RulebookEntry):
    """Subclass (archetype) definition."""
    parent_class: str = Field(description="Index of the parent class")
    subclass_flavor: str | None = Field(default=None, description="Flavor text describing the subclass")
    desc: list[str] = Field(default_factory=list, description="Description paragraphs")
    subclass_levels: dict[int, ClassLevelInfo] = Field(
        default_factory=dict,
        description="Level -> features gained from subclass"
    )
    spellcasting: SpellcastingInfo | None = Field(
        default=None,
        description="Subclass spellcasting (e.g., Eldritch Knight, Arcane Trickster)"
    )


class ClassDefinition(RulebookEntry):
    """Complete class definition with all level progression."""
    hit_die: int = Field(ge=6, le=12, description="Hit die size (6, 8, 10, or 12)")
    proficiencies: list[str] = Field(default_factory=list, description="Proficiency names")
    proficiency_choices: dict[str, Any] = Field(
        default_factory=dict,
        description="Proficiency choices (e.g., choose 2 from skills)"
    )
    saving_throws: list[str] = Field(description="Saving throw proficiencies (e.g., ['STR', 'CON'])")
    starting_equipment: list[str] = Field(default_factory=list, description="Starting equipment")
    starting_equipment_options: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Equipment choices"
    )
    spellcasting: SpellcastingInfo | None = Field(default=None, description="Spellcasting info if applicable")
    class_levels: dict[int, ClassLevelInfo] = Field(
        default_factory=dict,
        description="Level -> features/bonuses"
    )
    subclasses: list[str] = Field(default_factory=list, description="Available subclass indexes")
    subclass_level: int = Field(default=3, description="Level at which subclass is chosen")
    multi_classing: dict[str, Any] = Field(
        default_factory=dict,
        description="Multiclassing requirements and proficiencies"
    )


# =============================================================================
# Race Models
# =============================================================================

class AbilityBonus(BaseModel):
    """Ability score bonus from race or subrace."""
    ability_score: str = Field(description="Ability name (e.g., 'STR', 'DEX')")
    bonus: int = Field(description="Bonus value (typically +1 or +2)")


class RacialTrait(BaseModel):
    """A racial trait or feature."""
    index: str
    name: str
    desc: list[str] = Field(default_factory=list)


class SubraceDefinition(RulebookEntry):
    """Subrace definition."""
    parent_race: str = Field(description="Index of the parent race")
    desc: str | None = Field(default=None)
    ability_bonuses: list[AbilityBonus] = Field(default_factory=list)
    traits: list[RacialTrait] = Field(default_factory=list)
    starting_proficiencies: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class RaceDefinition(RulebookEntry):
    """Complete race definition."""
    speed: int = Field(default=30, description="Base walking speed in feet")
    ability_bonuses: list[AbilityBonus] = Field(default_factory=list)
    ability_bonus_options: dict[str, Any] | None = Field(
        default=None,
        description="Flexible ability bonus choices (e.g., Half-Elf)"
    )
    size: Size = Field(default=Size.MEDIUM)
    size_description: str | None = Field(default=None)
    alignment: str | None = Field(default=None, description="Typical alignment")
    age: str | None = Field(default=None, description="Age description")
    languages: list[str] = Field(default_factory=list)
    language_options: dict[str, Any] | None = Field(default=None)
    language_desc: str | None = Field(default=None)
    traits: list[RacialTrait] = Field(default_factory=list)
    starting_proficiencies: list[str] = Field(default_factory=list)
    starting_proficiency_options: dict[str, Any] | None = Field(default=None)
    subraces: list[str] = Field(default_factory=list, description="Available subrace indexes")


# =============================================================================
# Spell Models
# =============================================================================

class SpellDefinition(RulebookEntry):
    """Complete spell definition from SRD."""
    level: int = Field(ge=0, le=9, description="Spell level (0 = cantrip)")
    school: SpellSchool
    casting_time: str = Field(description="e.g., '1 action', '1 minute'")
    range: str = Field(description="e.g., '120 feet', 'Self', 'Touch'")
    duration: str = Field(description="e.g., 'Instantaneous', 'Concentration, up to 1 minute'")
    components: list[Literal["V", "S", "M"]] = Field(description="Verbal, Somatic, Material")
    material: str | None = Field(default=None, description="Material component description")
    ritual: bool = Field(default=False)
    concentration: bool = Field(default=False)
    desc: list[str] = Field(default_factory=list, description="Description paragraphs")
    higher_level: list[str] | None = Field(
        default=None,
        description="Effects when cast at higher levels"
    )
    classes: list[str] = Field(default_factory=list, description="Class indexes that can learn this spell")
    subclasses: list[str] = Field(default_factory=list, description="Subclass indexes with access")
    damage_type: str | None = Field(default=None)
    damage_at_slot_level: dict[str, str] | None = Field(default=None)
    damage_at_character_level: dict[str, str] | None = Field(default=None)
    dc_type: str | None = Field(default=None, description="Saving throw type if applicable")
    dc_success: str | None = Field(default=None, description="Effect on successful save")
    area_of_effect: dict[str, Any] | None = Field(default=None)

    @property
    def level_text(self) -> str:
        """Return human-readable level text."""
        if self.level == 0:
            return "Cantrip"
        ordinals = {1: "1st", 2: "2nd", 3: "3rd"}
        return f"{ordinals.get(self.level, f'{self.level}th')}-level"


# =============================================================================
# Monster Models
# =============================================================================

class ArmorClassInfo(BaseModel):
    """Armor class information for a monster."""
    type: str = Field(description="AC type (e.g., 'natural', 'armor')")
    value: int = Field(ge=1, le=30)
    armor: list[str] | None = Field(default=None, description="Armor worn if any")


class MonsterAbility(BaseModel):
    """Special ability of a monster."""
    name: str
    desc: str
    usage: dict[str, Any] | None = Field(default=None, description="Usage limits")
    dc: dict[str, Any] | None = Field(default=None, description="DC info if applicable")
    damage: list[dict[str, Any]] | None = Field(default=None)


class MonsterAction(BaseModel):
    """Action a monster can take."""
    name: str
    desc: str
    attack_bonus: int | None = Field(default=None)
    damage: list[dict[str, Any]] | None = Field(default=None)
    dc: dict[str, Any] | None = Field(default=None)
    usage: dict[str, Any] | None = Field(default=None)
    multiattack_type: str | None = Field(default=None)
    actions: list[dict[str, Any]] | None = Field(default=None, description="For multiattack")


class MonsterDefinition(RulebookEntry):
    """Complete monster stat block."""
    size: Size
    type: str = Field(description="Creature type (e.g., 'dragon', 'humanoid')")
    subtype: str | None = Field(default=None)
    alignment: str
    armor_class: list[ArmorClassInfo]
    hit_points: int = Field(ge=1)
    hit_dice: str = Field(description="e.g., '12d10+60'")
    hit_points_roll: str | None = Field(default=None)
    speed: dict[str, str] = Field(description="Speed by type (walk, fly, swim, etc.)")

    # Ability scores
    strength: int = Field(ge=1, le=30)
    dexterity: int = Field(ge=1, le=30)
    constitution: int = Field(ge=1, le=30)
    intelligence: int = Field(ge=1, le=30)
    wisdom: int = Field(ge=1, le=30)
    charisma: int = Field(ge=1, le=30)

    # Proficiencies and immunities
    proficiencies: list[dict[str, Any]] = Field(default_factory=list)
    damage_vulnerabilities: list[str] = Field(default_factory=list)
    damage_resistances: list[str] = Field(default_factory=list)
    damage_immunities: list[str] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)

    # Senses and languages
    senses: dict[str, str] = Field(default_factory=dict)
    languages: str = Field(default="")

    # Challenge rating
    challenge_rating: float = Field(ge=0, le=30)
    xp: int = Field(ge=0)
    proficiency_bonus: int | None = Field(default=None)

    # Abilities and actions
    special_abilities: list[MonsterAbility] = Field(default_factory=list)
    actions: list[MonsterAction] = Field(default_factory=list)
    reactions: list[MonsterAction] = Field(default_factory=list)
    legendary_actions: list[MonsterAction] | None = Field(default=None)
    lair_actions: list[dict[str, Any]] | None = Field(default=None)

    # Description
    desc: str | None = Field(default=None)

    def get_ability_modifier(self, ability: str) -> int:
        """Calculate ability modifier."""
        score = getattr(self, ability.lower(), 10)
        return (score - 10) // 2


# =============================================================================
# Feat, Background, Item Models
# =============================================================================

class Prerequisite(BaseModel):
    """Prerequisite for a feat."""
    type: str = Field(description="Type of prerequisite (ability_score, proficiency, spell, etc.)")
    ability_score: str | None = Field(default=None)
    minimum_score: int | None = Field(default=None)
    proficiency: str | None = Field(default=None)
    feature: str | None = Field(default=None)
    level: int | None = Field(default=None)


class FeatDefinition(RulebookEntry):
    """Feat definition."""
    desc: list[str] = Field(default_factory=list)
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    ability_score_increase: list[AbilityBonus] | None = Field(default=None)
    ability_score_choice: dict[str, Any] | None = Field(default=None)
    proficiencies: list[str] = Field(default_factory=list)


class BackgroundFeature(BaseModel):
    """Feature granted by a background."""
    name: str
    desc: list[str] = Field(default_factory=list)


class BackgroundDefinition(RulebookEntry):
    """Background definition."""
    desc: list[str] = Field(default_factory=list)
    starting_proficiencies: list[str] = Field(default_factory=list)
    starting_proficiency_options: dict[str, Any] | None = Field(default=None)
    language_options: dict[str, Any] | None = Field(default=None)
    starting_equipment: list[str] = Field(default_factory=list)
    starting_equipment_options: list[dict[str, Any]] = Field(default_factory=list)
    feature: BackgroundFeature | None = Field(default=None)
    personality_traits: dict[str, Any] | None = Field(default=None)
    ideals: dict[str, Any] | None = Field(default=None)
    bonds: dict[str, Any] | None = Field(default=None)
    flaws: dict[str, Any] | None = Field(default=None)


class ItemDefinition(RulebookEntry):
    """Magic item or equipment definition."""
    desc: list[str] = Field(default_factory=list)
    equipment_category: str = Field(description="Category (weapon, armor, adventuring-gear, etc.)")
    cost: dict[str, Any] | None = Field(default=None)
    weight: float | None = Field(default=None)

    # Weapon properties
    weapon_category: str | None = Field(default=None)
    weapon_range: str | None = Field(default=None)
    damage: dict[str, Any] | None = Field(default=None)
    two_handed_damage: dict[str, Any] | None = Field(default=None)
    range: dict[str, int] | None = Field(default=None, description="Normal/long range for ranged weapons")
    properties: list[str] = Field(default_factory=list)

    # Armor properties
    armor_category: str | None = Field(default=None)
    armor_class: dict[str, Any] | None = Field(default=None)
    str_minimum: int | None = Field(default=None)
    stealth_disadvantage: bool | None = Field(default=None)

    # Magic item properties
    rarity: ItemRarity | None = Field(default=None)
    requires_attunement: bool = Field(default=False)
    attunement_requirements: str | None = Field(default=None)


# =============================================================================
# Rulebook Container Models
# =============================================================================

class Rulebook(BaseModel):
    """
    Container for a complete rulebook.

    Can hold content from SRD, Open5e, or custom homebrew sources.
    """
    id: str = Field(description="Unique identifier for this rulebook")
    name: str = Field(description="Display name")
    version: str = Field(default="1.0")
    source: RulebookSource
    description: str | None = Field(default=None)
    loaded_at: datetime = Field(default_factory=datetime.now)

    # Content
    classes: dict[str, ClassDefinition] = Field(default_factory=dict)
    subclasses: dict[str, SubclassDefinition] = Field(default_factory=dict)
    races: dict[str, RaceDefinition] = Field(default_factory=dict)
    subraces: dict[str, SubraceDefinition] = Field(default_factory=dict)
    spells: dict[str, SpellDefinition] = Field(default_factory=dict)
    monsters: dict[str, MonsterDefinition] = Field(default_factory=dict)
    feats: dict[str, FeatDefinition] = Field(default_factory=dict)
    backgrounds: dict[str, BackgroundDefinition] = Field(default_factory=dict)
    items: dict[str, ItemDefinition] = Field(default_factory=dict)

    @property
    def content_counts(self) -> dict[str, int]:
        """Return count of each content type."""
        return {
            "classes": len(self.classes),
            "subclasses": len(self.subclasses),
            "races": len(self.races),
            "subraces": len(self.subraces),
            "spells": len(self.spells),
            "monsters": len(self.monsters),
            "feats": len(self.feats),
            "backgrounds": len(self.backgrounds),
            "items": len(self.items),
        }

    def stats_summary(self) -> str:
        """Return a formatted summary of content counts."""
        counts = self.content_counts
        non_empty = {k: v for k, v in counts.items() if v > 0}
        return ", ".join(f"{v} {k}" for k, v in non_empty.items())


class RulebookManifestEntry(BaseModel):
    """Entry in the rulebook manifest."""
    id: str
    source: RulebookSource
    version: str | None = Field(default=None)
    path: str | None = Field(default=None, description="Path to custom rulebook file")
    loaded_at: datetime


class RulebookManifest(BaseModel):
    """
    Manifest of active rulebooks for a campaign.

    Stored in {campaign}/rulebooks/manifest.json
    """
    active_rulebooks: list[RulebookManifestEntry] = Field(default_factory=list)
    priority: list[str] = Field(
        default_factory=list,
        description="Order of resolution (last wins)"
    )
    conflict_resolution: Literal["last_wins", "first_wins"] = Field(default="last_wins")
    updated_at: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "RulebookSource",
    "Size",
    "SpellSchool",
    "ItemRarity",
    # Base
    "RulebookEntry",
    # Spellcasting
    "SpellcastingInfo",
    "ClassLevelInfo",
    # Classes
    "ClassDefinition",
    "SubclassDefinition",
    # Races
    "RaceDefinition",
    "SubraceDefinition",
    "AbilityBonus",
    "RacialTrait",
    # Spells
    "SpellDefinition",
    # Monsters
    "MonsterDefinition",
    "MonsterAbility",
    "MonsterAction",
    "ArmorClassInfo",
    # Other content
    "FeatDefinition",
    "BackgroundDefinition",
    "BackgroundFeature",
    "ItemDefinition",
    "Prerequisite",
    # Containers
    "Rulebook",
    "RulebookManifest",
    "RulebookManifestEntry",
]
