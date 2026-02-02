"""
Character validation against loaded rulebook content.

This module provides validation logic to check characters against loaded rulebooks,
producing detailed reports with errors, warnings, and suggestions. Validation is
informational (warnings) not blocking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Character
    from .manager import RulebookManager


# =============================================================================
# Multiclass Requirements
# =============================================================================

MULTICLASS_REQUIREMENTS: dict[str, dict[str, int]] = {
    "barbarian": {"strength": 13},
    "bard": {"charisma": 13},
    "cleric": {"wisdom": 13},
    "druid": {"wisdom": 13},
    "fighter": {"strength": 13},  # OR dexterity: 13
    "monk": {"dexterity": 13, "wisdom": 13},
    "paladin": {"strength": 13, "charisma": 13},
    "ranger": {"dexterity": 13, "wisdom": 13},
    "rogue": {"dexterity": 13},
    "sorcerer": {"charisma": 13},
    "warlock": {"charisma": 13},
    "wizard": {"intelligence": 13},
}


# =============================================================================
# Validation Models
# =============================================================================

class ValidationSeverity(Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Character cannot be rules-legal
    WARNING = "warning"  # Possible issue, but allowed
    INFO = "info"        # Informational note


@dataclass
class ValidationIssue:
    """A single validation issue found during character validation."""
    severity: ValidationSeverity
    type: str           # e.g., "invalid_subclass", "missing_feature"
    message: str        # Human-readable message
    field: str          # e.g., "character_class.subclass"
    suggestion: str | None = None


@dataclass
class ValidationReport:
    """
    Complete validation report for a character.

    The report contains all issues found during validation, organized by severity.
    A character is considered valid if it has no ERROR-level issues.
    """
    character_id: str
    valid: bool         # True if no errors (warnings OK)
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Return all ERROR-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Return all WARNING-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def info(self) -> list[ValidationIssue]:
        """Return all INFO-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    def __str__(self) -> str:
        """Return a formatted summary of the validation report."""
        lines = [f"Validation Report for {self.character_id}"]
        lines.append(f"Status: {'✓ VALID' if self.valid else '✗ INVALID'}")
        lines.append(f"Issues: {len(self.errors)} errors, {len(self.warnings)} warnings, {len(self.info)} info")

        if self.errors:
            lines.append("\nErrors:")
            for issue in self.errors:
                lines.append(f"  - [{issue.type}] {issue.field}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")

        if self.warnings:
            lines.append("\nWarnings:")
            for issue in self.warnings:
                lines.append(f"  - [{issue.type}] {issue.field}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")

        if self.info:
            lines.append("\nInfo:")
            for issue in self.info:
                lines.append(f"  - [{issue.type}] {issue.field}: {issue.message}")
                if issue.suggestion:
                    lines.append(f"    Suggestion: {issue.suggestion}")

        return "\n".join(lines)


# =============================================================================
# Character Validator
# =============================================================================

class CharacterValidator:
    """
    Validates characters against loaded rulebook content.

    The validator checks character attributes against the rulebooks loaded in the
    RulebookManager, producing a detailed ValidationReport with any issues found.

    Validation is informational and not blocking:
    - ERROR: Character is not rules-legal (invalid subclass for class, etc.)
    - WARNING: Possible issue but allowed (unknown homebrew content, etc.)
    - INFO: Informational note (missing expected features, etc.)
    """

    def __init__(self, manager: RulebookManager):
        """
        Initialize the validator.

        Args:
            manager: RulebookManager with loaded rulebook sources
        """
        self.manager = manager

    def validate(self, character: Character) -> ValidationReport:
        """
        Validate a character against loaded rulebooks.

        Args:
            character: The character to validate

        Returns:
            ValidationReport with all issues found
        """
        issues: list[ValidationIssue] = []

        issues.extend(self._validate_class(character))
        issues.extend(self._validate_race(character))
        issues.extend(self._validate_ability_scores(character))
        issues.extend(self._validate_features(character))

        return ValidationReport(
            character_id=character.id,
            valid=not any(i.severity == ValidationSeverity.ERROR for i in issues),
            issues=issues,
        )

    def _validate_class(self, character: Character) -> list[ValidationIssue]:
        """Validate character class and subclass."""
        issues: list[ValidationIssue] = []

        # Normalize class name to index format (lowercase with hyphens)
        class_index = character.character_class.name.lower().replace(" ", "-")
        class_def = self.manager.get_class(class_index)

        if class_def is None:
            # Class not found - may be homebrew
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                type="unknown_class",
                message=f"Class '{character.character_class.name}' not found in loaded rulebooks. This may be homebrew content.",
                field="character_class.name",
                suggestion="If this is custom content, consider adding it to a custom rulebook source.",
            ))
            return issues

        # Validate subclass if provided
        if character.character_class.subclass:
            subclass_normalized = character.character_class.subclass.lower().replace(" ", "-")

            # Check if subclass is in the class's available subclasses (case-insensitive)
            valid_subclasses_lower = [sc.lower() for sc in class_def.subclasses]

            if subclass_normalized not in valid_subclasses_lower:
                # Try to get the subclass directly from the manager
                subclass_def = self.manager.get_subclass(subclass_normalized)

                if subclass_def is None or subclass_def.parent_class != class_index:
                    # Invalid subclass
                    if class_def.subclasses:
                        valid_names = ", ".join(class_def.subclasses)
                        suggestion = f"Valid subclasses for {class_def.name}: {valid_names}"
                    else:
                        suggestion = f"{class_def.name} has no subclasses defined in loaded rulebooks."

                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        type="invalid_subclass",
                        message=f"Subclass '{character.character_class.subclass}' is not valid for class '{character.character_class.name}'.",
                        field="character_class.subclass",
                        suggestion=suggestion,
                    ))

        return issues

    def _validate_race(self, character: Character) -> list[ValidationIssue]:
        """Validate character race and subrace."""
        issues: list[ValidationIssue] = []

        # Normalize race name to index format
        race_index = character.race.name.lower().replace(" ", "-")
        race_def = self.manager.get_race(race_index)

        if race_def is None:
            # Race not found - may be homebrew
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                type="unknown_race",
                message=f"Race '{character.race.name}' not found in loaded rulebooks. This may be homebrew content.",
                field="race.name",
                suggestion="If this is custom content, consider adding it to a custom rulebook source.",
            ))
            return issues

        # Validate subrace if provided
        if character.race.subrace:
            subrace_normalized = character.race.subrace.lower().replace(" ", "-")

            # Check if subrace is in the race's available subraces (case-insensitive)
            valid_subraces_lower = [sr.lower() for sr in race_def.subraces]

            if subrace_normalized not in valid_subraces_lower:
                # Try to get the subrace directly from the manager
                subrace_def = self.manager.get_subrace(subrace_normalized)

                if subrace_def is None or subrace_def.parent_race != race_index:
                    # Invalid subrace
                    if race_def.subraces:
                        valid_names = ", ".join(race_def.subraces)
                        suggestion = f"Valid subraces for {race_def.name}: {valid_names}"
                    else:
                        suggestion = f"{race_def.name} has no subraces defined in loaded rulebooks."

                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        type="invalid_subrace",
                        message=f"Subrace '{character.race.subrace}' is not valid for race '{character.race.name}'.",
                        field="race.subrace",
                        suggestion=suggestion,
                    ))

        return issues

    def _validate_ability_scores(self, character: Character) -> list[ValidationIssue]:
        """Validate ability scores meet multiclass requirements."""
        issues: list[ValidationIssue] = []

        # Normalize class name
        class_name = character.character_class.name.lower().replace(" ", "-")

        # Get multiclass requirements
        requirements = MULTICLASS_REQUIREMENTS.get(class_name)
        if not requirements:
            # No requirements defined or unknown class
            return issues

        # Check each requirement
        unmet_requirements: list[str] = []

        for ability, minimum in requirements.items():
            # Special case for fighter: strength OR dexterity
            if class_name == "fighter":
                str_score = character.abilities.get("strength")
                dex_score = character.abilities.get("dexterity")
                if str_score and dex_score:
                    if str_score.score >= 13 or dex_score.score >= 13:
                        continue
                    else:
                        unmet_requirements.append("Strength 13 OR Dexterity 13")
                        continue

            # Normal requirement check
            if ability in character.abilities:
                score = character.abilities[ability].score
                if score < minimum:
                    unmet_requirements.append(f"{ability.capitalize()} {minimum}")

        if unmet_requirements:
            req_text = ", ".join(unmet_requirements)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                type="multiclass_requirements",
                message=f"Character does not meet multiclass requirements for {character.character_class.name}. Required: {req_text}",
                field="abilities",
                suggestion="This is informational. If the character is not multiclassing, this can be ignored.",
            ))

        return issues

    def _validate_features(self, character: Character) -> list[ValidationIssue]:
        """Check for missing class features at character's level."""
        issues: list[ValidationIssue] = []

        # Normalize class name
        class_index = character.character_class.name.lower().replace(" ", "-")
        class_def = self.manager.get_class(class_index)

        if class_def is None:
            # Can't validate if class not found
            return issues

        # Get expected features for character's level
        expected_features: set[str] = set()

        for level in range(1, character.character_class.level + 1):
            level_info = class_def.class_levels.get(level)
            if level_info:
                expected_features.update(level_info.features)

        # Normalize character features for comparison (lowercase)
        character_features_lower = {f.lower() for f in character.features_and_traits}

        # Find missing features
        missing_features: list[str] = []
        for feature in expected_features:
            if feature.lower() not in character_features_lower:
                missing_features.append(feature)

        if missing_features:
            # Group features by count for better readability
            if len(missing_features) <= 3:
                feature_list = ", ".join(missing_features)
                message = f"Character may be missing class features: {feature_list}"
            else:
                feature_list = ", ".join(missing_features[:3])
                message = f"Character may be missing {len(missing_features)} class features including: {feature_list}"

            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                type="missing_features",
                message=message,
                field="features_and_traits",
                suggestion=f"Consider adding expected features for a level {character.character_class.level} {character.character_class.name}.",
            ))

        return issues


__all__ = [
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationReport",
    "CharacterValidator",
    "MULTICLASS_REQUIREMENTS",
]
