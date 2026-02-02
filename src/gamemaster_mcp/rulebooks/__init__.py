"""
Rulebook management system for gamemaster-mcp.

This module provides:
- Data models for D&D 5e rules (classes, races, spells, monsters, etc.)
- Integration with 5e-srd-api for official SRD content
- Support for custom homebrew rulebooks (JSON/YAML)
- RulebookManager for orchestrating multiple sources
- Character validation against loaded rules
"""

from .models import (
    # Core rulebook model
    Rulebook,
    RulebookManifest,
    # Class models
    ClassDefinition,
    SubclassDefinition,
    ClassLevelInfo,
    SpellcastingInfo,
    # Race models
    RaceDefinition,
    SubraceDefinition,
    AbilityBonus,
    RacialTrait,
    # Spell model
    SpellDefinition,
    # Monster model
    MonsterDefinition,
    MonsterAbility,
    MonsterAction,
    ArmorClassInfo,
    # Other content
    FeatDefinition,
    BackgroundDefinition,
    ItemDefinition,
)
from .manager import RulebookManager, RulebookManagerError
from .validators import (
    CharacterValidator,
    ValidationSeverity,
    ValidationIssue,
    ValidationReport,
)

__all__ = [
    # Manager
    "RulebookManager",
    "RulebookManagerError",
    # Validators
    "CharacterValidator",
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationReport",
    # Core
    "Rulebook",
    "RulebookManifest",
    # Classes
    "ClassDefinition",
    "SubclassDefinition",
    "ClassLevelInfo",
    "SpellcastingInfo",
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
    # Other
    "FeatDefinition",
    "BackgroundDefinition",
    "ItemDefinition",
]
