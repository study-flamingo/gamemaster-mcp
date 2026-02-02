"""
Tests for rulebook sources.
"""

import asyncio
import pytest
from pathlib import Path

from gamemaster_mcp.rulebooks.sources import (
    RulebookSourceBase,
    CustomSource,
    CustomSourceError,
    SearchResult,
    ContentCounts,
)
from gamemaster_mcp.rulebooks.models import RulebookSource


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "rulebooks"


def run_async(coro):
    """Helper to run async code in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestContentCounts:
    """Test ContentCounts dataclass."""

    def test_empty_counts(self):
        counts = ContentCounts()
        assert counts.classes == 0
        assert counts.spells == 0
        assert str(counts) == "empty"

    def test_counts_to_dict(self):
        counts = ContentCounts(classes=3, spells=10, monsters=5)
        d = counts.to_dict()
        assert d["classes"] == 3
        assert d["spells"] == 10
        assert d["monsters"] == 5

    def test_counts_str(self):
        counts = ContentCounts(classes=2, races=3)
        s = str(counts)
        assert "2 classes" in s
        assert "3 races" in s
        assert "spells" not in s  # Zero values excluded


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_search_result_to_dict(self):
        result = SearchResult(
            index="fireball",
            name="Fireball",
            category="spell",
            source="srd-2014",
            summary="A bright streak flashes...",
        )
        d = result.to_dict()
        assert d["index"] == "fireball"
        assert d["name"] == "Fireball"
        assert d["category"] == "spell"
        assert d["source"] == "srd-2014"


class TestCustomSourceJSON:
    """Test CustomSource with JSON files."""

    @pytest.fixture
    def json_source(self):
        """Create a CustomSource from JSON fixture."""
        source = CustomSource(FIXTURES_DIR / "homebrew_races.json")
        run_async(source.load())
        return source

    def test_load_json(self, json_source):
        """Test loading a JSON rulebook."""
        assert json_source.is_loaded
        assert json_source.loaded_at is not None
        assert json_source.name == "Test Homebrew Races"

    def test_source_id_derived(self):
        """Test that source_id is derived from filename."""
        source = CustomSource(FIXTURES_DIR / "homebrew_races.json")
        assert source.source_id == "custom-homebrew-races"
        assert source.source_type == RulebookSource.CUSTOM

    def test_get_race(self, json_source):
        """Test getting a race by index."""
        race = json_source.get_race("aetherborn")
        assert race is not None
        assert race.name == "Aetherborn"
        assert race.speed == 30
        assert len(race.ability_bonuses) == 2
        assert race.source == "custom-homebrew-races"

    def test_get_nonexistent_race(self, json_source):
        """Test getting a race that doesn't exist."""
        assert json_source.get_race("nonexistent") is None

    def test_content_counts(self, json_source):
        """Test content counts."""
        counts = json_source.content_counts()
        assert counts.races == 2
        assert counts.classes == 0
        assert counts.spells == 0

    def test_search(self, json_source):
        """Test searching content."""
        results = list(json_source.search("aether"))
        assert len(results) == 1
        assert results[0].name == "Aetherborn"
        assert results[0].category == "race"

    def test_search_with_category_filter(self, json_source):
        """Test searching with category filter."""
        # Search in races only
        results = list(json_source.search("war", categories=["race"]))
        assert len(results) == 1
        assert results[0].name == "Warforged"

        # Search in spells only (should find nothing)
        results = list(json_source.search("war", categories=["spell"]))
        assert len(results) == 0


class TestCustomSourceYAML:
    """Test CustomSource with YAML files."""

    @pytest.fixture
    def yaml_source(self):
        """Create a CustomSource from YAML fixture."""
        source = CustomSource(FIXTURES_DIR / "house_rules.yaml")
        run_async(source.load())
        return source

    def test_load_yaml(self, yaml_source):
        """Test loading a YAML rulebook."""
        assert yaml_source.is_loaded
        assert yaml_source.name == "House Rules"

    def test_get_spell(self, yaml_source):
        """Test getting a spell from YAML."""
        spell = yaml_source.get_spell("eldritch-blast-variant")
        assert spell is not None
        assert spell.name == "Eldritch Blast Variant"
        assert spell.level == 0
        assert "warlock" in spell.classes

    def test_get_feat(self, yaml_source):
        """Test getting a feat from YAML."""
        feat = yaml_source.get_feat("spellblade")
        assert feat is not None
        assert feat.name == "Spellblade"
        assert len(feat.prerequisites) == 1
        assert feat.prerequisites[0].ability_score == "INT"

    def test_content_counts_yaml(self, yaml_source):
        """Test content counts from YAML."""
        counts = yaml_source.content_counts()
        assert counts.spells == 1
        assert counts.feats == 1


class TestCustomSourceErrors:
    """Test error handling in CustomSource."""

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        source = CustomSource(FIXTURES_DIR / "nonexistent.json")

        with pytest.raises(CustomSourceError, match="not found"):
            run_async(source.load())

    def test_unsupported_format(self, tmp_path):
        """Test error for unsupported file format."""
        bad_file = tmp_path / "rulebook.txt"
        bad_file.write_text("not a rulebook")

        source = CustomSource(bad_file)
        with pytest.raises(CustomSourceError, match="Unsupported file format"):
            run_async(source.load())

    def test_invalid_json(self, tmp_path):
        """Test error for invalid JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json")

        source = CustomSource(bad_file)
        with pytest.raises(CustomSourceError, match="Failed to parse"):
            run_async(source.load())

    def test_invalid_yaml(self, tmp_path):
        """Test error for invalid YAML."""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text(":\n  - invalid\n  yaml: [unclosed")

        source = CustomSource(bad_file)
        with pytest.raises(CustomSourceError, match="Failed to parse"):
            run_async(source.load())

    def test_not_object(self, tmp_path):
        """Test error when top-level is not an object."""
        bad_file = tmp_path / "array.json"
        bad_file.write_text("[1, 2, 3]")

        source = CustomSource(bad_file)
        with pytest.raises(CustomSourceError, match="must be a JSON/YAML object"):
            run_async(source.load())


class TestCustomSourceCustomId:
    """Test CustomSource with custom source ID."""

    def test_custom_source_id(self):
        """Test providing a custom source ID."""
        source = CustomSource(
            FIXTURES_DIR / "homebrew_races.json",
            source_id="my-custom-id"
        )
        run_async(source.load())

        assert source.source_id == "my-custom-id"

        # Check that content has the custom source
        race = source.get_race("aetherborn")
        assert race.source == "my-custom-id"


class TestCustomSourcePartialRulebook:
    """Test partial rulebooks (only some content types)."""

    def test_partial_rulebook(self, tmp_path):
        """Test a rulebook with only races."""
        partial = tmp_path / "partial.json"
        partial.write_text("""{
            "name": "Partial Rulebook",
            "content": {
                "races": [
                    {"name": "Test Race", "speed": 30, "languages": ["Common"]}
                ]
            }
        }""")

        source = CustomSource(partial)
        run_async(source.load())

        counts = source.content_counts()
        assert counts.races == 1
        assert counts.classes == 0
        assert counts.spells == 0

        # Other getters should return None
        assert source.get_class("any") is None
        assert source.get_spell("any") is None
