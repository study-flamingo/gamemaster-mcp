"""
Tests for character validation against rulebooks.
"""

import asyncio
import pytest
from pathlib import Path

from gamemaster_mcp.models import Character, CharacterClass, Race, AbilityScore
from gamemaster_mcp.rulebooks import (
    CharacterValidator,
    ValidationSeverity,
    ValidationReport,
    RulebookManager,
)
from gamemaster_mcp.rulebooks.models import (
    ClassDefinition,
    SubclassDefinition,
    RaceDefinition,
    SubraceDefinition,
    ClassLevelInfo,
    RulebookSource,
)
from gamemaster_mcp.rulebooks.sources.base import (
    RulebookSourceBase,
    SearchResult,
    ContentCounts,
)


def run_async(coro):
    """Helper to run async code in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class MockRulebookSource(RulebookSourceBase):
    """Mock rulebook source for testing."""

    def __init__(self, source_id: str = "test-source"):
        super().__init__(source_id, RulebookSource.CUSTOM, name=source_id)
        self._classes: dict[str, ClassDefinition] = {}
        self._subclasses: dict[str, SubclassDefinition] = {}
        self._races: dict[str, RaceDefinition] = {}
        self._subraces: dict[str, SubraceDefinition] = {}

    async def load(self) -> None:
        """Load the source."""
        self._loaded = True

    def add_class(self, class_def: ClassDefinition) -> None:
        """Add a class to the mock source."""
        self._classes[class_def.index] = class_def

    def add_subclass(self, subclass_def: SubclassDefinition) -> None:
        """Add a subclass to the mock source."""
        self._subclasses[subclass_def.index] = subclass_def

    def add_race(self, race_def: RaceDefinition) -> None:
        """Add a race to the mock source."""
        self._races[race_def.index] = race_def

    def add_subrace(self, subrace_def: SubraceDefinition) -> None:
        """Add a subrace to the mock source."""
        self._subraces[subrace_def.index] = subrace_def

    def get_class(self, index: str) -> ClassDefinition | None:
        return self._classes.get(index)

    def get_subclass(self, index: str) -> SubclassDefinition | None:
        return self._subclasses.get(index)

    def get_race(self, index: str) -> RaceDefinition | None:
        return self._races.get(index)

    def get_subrace(self, index: str) -> SubraceDefinition | None:
        return self._subraces.get(index)

    def get_spell(self, index: str):
        return None

    def get_monster(self, index: str):
        return None

    def get_feat(self, index: str):
        return None

    def get_background(self, index: str):
        return None

    def get_item(self, index: str):
        return None

    def search(self, query: str, categories=None):
        return []

    def content_counts(self) -> ContentCounts:
        return ContentCounts(
            classes=len(self._classes),
            subclasses=len(self._subclasses),
            races=len(self._races),
            subraces=len(self._subraces),
        )


@pytest.fixture
def mock_source():
    """Create a mock rulebook source with SRD-like content."""
    source = MockRulebookSource("test-srd")

    # Add wizard class
    wizard_class = ClassDefinition(
        index="wizard",
        name="Wizard",
        source="test-srd",
        hit_die=6,
        saving_throws=["INT", "WIS"],
        subclasses=["evocation", "abjuration"],
        subclass_level=2,
        class_levels={
            1: ClassLevelInfo(
                level=1,
                proficiency_bonus=2,
                features=["Spellcasting", "Arcane Recovery"],
            ),
            2: ClassLevelInfo(
                level=2,
                proficiency_bonus=2,
                features=["Arcane Tradition"],
            ),
            3: ClassLevelInfo(
                level=3,
                proficiency_bonus=2,
                features=[],
            ),
            4: ClassLevelInfo(
                level=4,
                proficiency_bonus=2,
                features=["Ability Score Improvement"],
            ),
            5: ClassLevelInfo(
                level=5,
                proficiency_bonus=3,
                features=[],
            ),
        },
    )
    source.add_class(wizard_class)

    # Add evocation subclass
    evocation_subclass = SubclassDefinition(
        index="evocation",
        name="School of Evocation",
        source="test-srd",
        parent_class="wizard",
        subclass_levels={
            2: ClassLevelInfo(
                level=2,
                proficiency_bonus=2,
                features=["Evocation Savant", "Sculpt Spells"],
            ),
        },
    )
    source.add_subclass(evocation_subclass)

    # Add fighter class
    fighter_class = ClassDefinition(
        index="fighter",
        name="Fighter",
        source="test-srd",
        hit_die=10,
        saving_throws=["STR", "CON"],
        subclasses=["champion", "battle-master"],
        subclass_level=3,
        class_levels={
            1: ClassLevelInfo(
                level=1,
                proficiency_bonus=2,
                features=["Fighting Style", "Second Wind"],
            ),
            2: ClassLevelInfo(
                level=2,
                proficiency_bonus=2,
                features=["Action Surge"],
            ),
            3: ClassLevelInfo(
                level=3,
                proficiency_bonus=2,
                features=["Martial Archetype"],
            ),
        },
    )
    source.add_class(fighter_class)

    # Add champion subclass
    champion_subclass = SubclassDefinition(
        index="champion",
        name="Champion",
        source="test-srd",
        parent_class="fighter",
        subclass_levels={
            3: ClassLevelInfo(
                level=3,
                proficiency_bonus=2,
                features=["Improved Critical"],
            ),
        },
    )
    source.add_subclass(champion_subclass)

    # Add human race
    human_race = RaceDefinition(
        index="human",
        name="Human",
        source="test-srd",
        speed=30,
        subraces=[],
    )
    source.add_race(human_race)

    # Add dwarf race
    dwarf_race = RaceDefinition(
        index="dwarf",
        name="Dwarf",
        source="test-srd",
        speed=25,
        subraces=["hill-dwarf", "mountain-dwarf"],
    )
    source.add_race(dwarf_race)

    # Add mountain dwarf subrace
    mountain_dwarf = SubraceDefinition(
        index="mountain-dwarf",
        name="Mountain Dwarf",
        source="test-srd",
        parent_race="dwarf",
    )
    source.add_subrace(mountain_dwarf)

    # Add elf race
    elf_race = RaceDefinition(
        index="elf",
        name="Elf",
        source="test-srd",
        speed=30,
        subraces=["high-elf", "wood-elf"],
    )
    source.add_race(elf_race)

    return source


@pytest.fixture
def manager_with_mock(mock_source):
    """Create a RulebookManager with mock source loaded."""
    manager = RulebookManager()
    run_async(manager.load_source(mock_source))
    yield manager
    run_async(manager.close())


@pytest.fixture
def validator(manager_with_mock):
    """Create a CharacterValidator with mock source loaded."""
    return CharacterValidator(manager_with_mock)


@pytest.fixture
def valid_wizard():
    """Create a valid wizard character."""
    return Character(
        id="test-wizard",
        name="Gandalf",
        character_class=CharacterClass(
            name="wizard",
            level=5,
            subclass="evocation",
        ),
        race=Race(
            name="human",
            subrace=None,
        ),
        abilities={
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=12),
            "intelligence": AbilityScore(score=16),
            "wisdom": AbilityScore(score=13),
            "charisma": AbilityScore(score=8),
        },
        features_and_traits=[
            "Spellcasting",
            "Arcane Recovery",
            "Evocation Savant",
            "Sculpt Spells",
        ],
    )


@pytest.fixture
def valid_dwarf_fighter():
    """Create a valid dwarf fighter character."""
    return Character(
        id="test-fighter",
        name="Gimli",
        character_class=CharacterClass(
            name="fighter",
            level=3,
            subclass="champion",
        ),
        race=Race(
            name="dwarf",
            subrace="mountain-dwarf",
        ),
        abilities={
            "strength": AbilityScore(score=16),
            "dexterity": AbilityScore(score=12),
            "constitution": AbilityScore(score=15),
            "intelligence": AbilityScore(score=10),
            "wisdom": AbilityScore(score=11),
            "charisma": AbilityScore(score=8),
        },
        features_and_traits=[
            "Fighting Style",
            "Second Wind",
            "Action Surge",
            "Improved Critical",
        ],
    )


class TestValidationReport:
    """Test ValidationReport functionality."""

    def test_valid_report_properties(self):
        """Test that ValidationReport properties work correctly."""
        report = ValidationReport(
            character_id="test",
            valid=True,
            issues=[],
        )
        assert report.errors == []
        assert report.warnings == []
        assert report.info == []

    def test_report_with_mixed_issues(self):
        """Test ValidationReport with different severity levels."""
        from gamemaster_mcp.rulebooks.validators import ValidationIssue

        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                type="test_error",
                message="Error message",
                field="test.field",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                type="test_warning",
                message="Warning message",
                field="test.field",
            ),
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                type="test_info",
                message="Info message",
                field="test.field",
            ),
        ]

        report = ValidationReport(
            character_id="test",
            valid=False,
            issues=issues,
        )

        assert len(report.errors) == 1
        assert len(report.warnings) == 1
        assert len(report.info) == 1
        assert report.errors[0].type == "test_error"
        assert report.warnings[0].type == "test_warning"
        assert report.info[0].type == "test_info"

    def test_report_string_representation(self):
        """Test that ValidationReport can be converted to string."""
        from gamemaster_mcp.rulebooks.validators import ValidationIssue

        report = ValidationReport(
            character_id="test-char",
            valid=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    type="test_error",
                    message="Test error",
                    field="test.field",
                    suggestion="Fix it",
                ),
            ],
        )

        report_str = str(report)
        assert "test-char" in report_str
        assert "INVALID" in report_str
        assert "Test error" in report_str
        assert "Fix it" in report_str


class TestCharacterValidator:
    """Test CharacterValidator functionality."""

    def test_valid_srd_character_passes(self, validator, valid_wizard):
        """Test that a valid SRD character passes validation."""
        report = validator.validate(valid_wizard)

        # Should have no errors
        assert report.valid
        assert len(report.errors) == 0

    def test_valid_dwarf_fighter_passes(self, validator, valid_dwarf_fighter):
        """Test that a valid dwarf fighter passes validation."""
        report = validator.validate(valid_dwarf_fighter)

        # Should have no errors
        assert report.valid
        assert len(report.errors) == 0

    def test_unknown_class_gives_warning(self, validator):
        """Test that an unknown class produces a warning."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="blood-hunter",  # Homebrew class
                level=1,
            ),
            race=Race(name="human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=10),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be valid (warning, not error)
        assert report.valid
        assert len(report.warnings) > 0

        # Find the unknown class warning
        class_warnings = [w for w in report.warnings if w.type == "unknown_class"]
        assert len(class_warnings) == 1
        assert "blood-hunter" in class_warnings[0].message.lower()

    def test_invalid_subclass_gives_error(self, validator):
        """Test that an invalid subclass produces an error."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="wizard",
                level=5,
                subclass="bladesinger",  # Valid in other sources, but not in SRD
            ),
            race=Race(name="human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=16),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be invalid
        assert not report.valid
        assert len(report.errors) > 0

        # Find the invalid subclass error
        subclass_errors = [e for e in report.errors if e.type == "invalid_subclass"]
        assert len(subclass_errors) == 1
        assert "bladesinger" in subclass_errors[0].message.lower()
        assert subclass_errors[0].suggestion is not None

    def test_invalid_subrace_gives_error(self, validator):
        """Test that an invalid subrace produces an error."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="fighter",
                level=1,
            ),
            race=Race(
                name="elf",
                subrace="sea-elf",  # Not in SRD
            ),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=10),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be invalid
        assert not report.valid
        assert len(report.errors) > 0

        # Find the invalid subrace error
        subrace_errors = [e for e in report.errors if e.type == "invalid_subrace"]
        assert len(subrace_errors) == 1
        assert "sea-elf" in subrace_errors[0].message.lower()
        assert subrace_errors[0].suggestion is not None

    def test_unknown_race_gives_warning(self, validator):
        """Test that an unknown race produces a warning."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="wizard",
                level=1,
            ),
            race=Race(
                name="warforged",  # Not in SRD
            ),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=16),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be valid (warning, not error)
        assert report.valid
        assert len(report.warnings) > 0

        # Find the unknown race warning
        race_warnings = [w for w in report.warnings if w.type == "unknown_race"]
        assert len(race_warnings) == 1
        assert "warforged" in race_warnings[0].message.lower()

    def test_multiclass_requirements_warning(self, validator):
        """Test that unmet multiclass requirements produce a warning."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="wizard",
                level=5,
            ),
            race=Race(name="human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=12),  # Below 13 requirement
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be valid (warning, not error)
        assert report.valid

        # Find the multiclass requirements warning
        mc_warnings = [w for w in report.warnings if w.type == "multiclass_requirements"]
        assert len(mc_warnings) == 1
        assert "intelligence" in mc_warnings[0].message.lower()

    def test_multiclass_requirements_met(self, validator, valid_wizard):
        """Test that characters meeting multiclass requirements don't get warnings."""
        report = validator.validate(valid_wizard)

        # Should have no multiclass warnings (intelligence is 16)
        mc_warnings = [w for w in report.warnings if w.type == "multiclass_requirements"]
        assert len(mc_warnings) == 0

    def test_fighter_multiclass_str_or_dex(self, validator):
        """Test that fighter multiclass allows STR OR DEX."""
        # Test with high DEX but low STR
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="fighter",
                level=3,
            ),
            race=Race(name="human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=14),  # Meets requirement
                "constitution": AbilityScore(score=12),
                "intelligence": AbilityScore(score=10),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should have no multiclass warnings (DEX meets requirement)
        mc_warnings = [w for w in report.warnings if w.type == "multiclass_requirements"]
        assert len(mc_warnings) == 0

        # Test with neither STR nor DEX
        character.abilities["dexterity"] = AbilityScore(score=10)
        report = validator.validate(character)

        # Should have multiclass warning
        mc_warnings = [w for w in report.warnings if w.type == "multiclass_requirements"]
        assert len(mc_warnings) == 1

    def test_missing_features_gives_info(self, validator):
        """Test that missing class features produce info-level issues."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="wizard",
                level=5,
            ),
            race=Race(name="human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=16),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
            features_and_traits=[],  # No features
        )

        report = validator.validate(character)

        # Should be valid (info, not error)
        assert report.valid
        assert len(report.info) > 0

        # Find the missing features info
        feature_info = [i for i in report.info if i.type == "missing_features"]
        assert len(feature_info) == 1
        assert feature_info[0].suggestion is not None

    def test_case_insensitive_class_name(self, validator):
        """Test that class names are case-insensitive."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="Wizard",  # Capital W
                level=5,
                subclass="Evocation",  # Capital E
            ),
            race=Race(name="Human"),  # Capital H
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=16),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should have no errors (case-insensitive matching)
        assert report.valid

    def test_multiple_validation_errors(self, validator):
        """Test that multiple errors are all reported."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="wizard",
                level=5,
                subclass="invalid-subclass",  # Invalid subclass
            ),
            race=Race(
                name="elf",
                subrace="invalid-subrace",  # Invalid subrace
            ),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=10),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be invalid with multiple errors
        assert not report.valid
        assert len(report.errors) >= 2

        error_types = {e.type for e in report.errors}
        assert "invalid_subclass" in error_types
        assert "invalid_subrace" in error_types

    def test_empty_character(self, validator):
        """Test validation of a minimal character."""
        character = Character(
            id="test",
            name="Test",
            character_class=CharacterClass(
                name="fighter",
                level=1,
            ),
            race=Race(name="human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=10),
                "constitution": AbilityScore(score=10),
                "intelligence": AbilityScore(score=10),
                "wisdom": AbilityScore(score=10),
                "charisma": AbilityScore(score=10),
            },
        )

        report = validator.validate(character)

        # Should be valid (minimal character is OK)
        assert report.valid
