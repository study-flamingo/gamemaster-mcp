"""
Tests for RulebookManager.

Tests cover source loading, priority resolution, search, and manifest persistence.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gamemaster_mcp.rulebooks import RulebookManager, RulebookManagerError
from gamemaster_mcp.rulebooks.models import (
    ClassDefinition,
    RaceDefinition,
    SpellDefinition,
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


class MockSource(RulebookSourceBase):
    """Mock source for testing."""

    def __init__(self, source_id: str, classes=None, races=None, spells=None):
        super().__init__(source_id, RulebookSource.CUSTOM, name=source_id)
        self._classes = classes or {}
        self._races = races or {}
        self._spells = spells or {}

    async def load(self) -> None:
        self._loaded = True

    def get_class(self, index: str):
        return self._classes.get(index)

    def get_subclass(self, index: str):
        return None

    def get_race(self, index: str):
        return self._races.get(index)

    def get_subrace(self, index: str):
        return None

    def get_spell(self, index: str):
        return self._spells.get(index)

    def get_monster(self, index: str):
        return None

    def get_feat(self, index: str):
        return None

    def get_background(self, index: str):
        return None

    def get_item(self, index: str):
        return None

    def search(self, query: str, categories=None, limit: int = 20):
        query_lower = query.lower()
        for cls in self._classes.values():
            if query_lower in cls.name.lower():
                yield SearchResult(cls.index, cls.name, "class", self.source_id)
        for race in self._races.values():
            if query_lower in race.name.lower():
                yield SearchResult(race.index, race.name, "race", self.source_id)
        for spell in self._spells.values():
            if query_lower in spell.name.lower():
                yield SearchResult(spell.index, spell.name, "spell", self.source_id)

    def content_counts(self) -> ContentCounts:
        return ContentCounts(
            classes=len(self._classes),
            races=len(self._races),
            spells=len(self._spells),
        )


# Sample test data
WIZARD_CLASS = ClassDefinition(
    index="wizard",
    name="Wizard",
    hit_die=6,
    saving_throws=["INT", "WIS"],
    source="srd-2014",
)

WIZARD_HOMEBREW = ClassDefinition(
    index="wizard",
    name="Wizard (Homebrew)",
    hit_die=8,  # Modified
    saving_throws=["INT", "WIS"],
    source="homebrew",
)

FIGHTER_CLASS = ClassDefinition(
    index="fighter",
    name="Fighter",
    hit_die=10,
    saving_throws=["STR", "CON"],
    source="srd-2014",
)

ELF_RACE = RaceDefinition(
    index="elf",
    name="Elf",
    speed=30,
    source="srd-2014",
)

FIREBALL_SPELL = SpellDefinition(
    index="fireball",
    name="Fireball",
    level=3,
    school="Evocation",
    casting_time="1 action",
    range="150 feet",
    duration="Instantaneous",
    components=["V", "S", "M"],
    source="srd-2014",
)


class TestRulebookManagerInit:
    """Test RulebookManager initialization."""

    def test_init_without_campaign_dir(self):
        manager = RulebookManager()
        assert manager.campaign_dir is None
        assert len(manager.sources) == 0
        assert len(manager.priority) == 0

    def test_init_with_campaign_dir(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        assert manager.campaign_dir == tmp_path
        assert (tmp_path / "rulebooks").exists()


class TestSourceLoading:
    """Test source loading and unloading."""

    def test_load_source(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource("test-source", classes={"wizard": WIZARD_CLASS})

        async def run_test():
            await manager.load_source(source)

            assert "test-source" in manager.source_ids
            assert manager.is_loaded("test-source")
            assert manager.priority == ["test-source"]

        run_async(run_test())

    def test_load_multiple_sources(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("source-1")
        source2 = MockSource("source-2")

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)

            assert manager.source_ids == ["source-1", "source-2"]
            assert manager.priority == ["source-1", "source-2"]

        run_async(run_test())

    def test_unload_source(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource("test-source")

        async def run_test():
            await manager.load_source(source)
            assert manager.is_loaded("test-source")

            result = manager.unload_source("test-source")
            assert result is True
            assert not manager.is_loaded("test-source")
            assert manager.source_ids == []

        run_async(run_test())

    def test_unload_nonexistent_source(self):
        manager = RulebookManager()
        result = manager.unload_source("nonexistent")
        assert result is False

    def test_reload_source_updates_priority(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("source-1")
        source2 = MockSource("source-2")
        source1_new = MockSource("source-1")  # Same ID, new instance

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)
            await manager.load_source(source1_new)  # Reload source-1

            # source-1 should move to end
            assert manager.priority == ["source-2", "source-1"]

        run_async(run_test())


class TestPriorityResolution:
    """Test priority-based content resolution."""

    def test_last_wins_priority(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source_srd = MockSource("srd", classes={"wizard": WIZARD_CLASS})
        source_homebrew = MockSource("homebrew", classes={"wizard": WIZARD_HOMEBREW})

        async def run_test():
            await manager.load_source(source_srd)
            await manager.load_source(source_homebrew)

            # Homebrew wizard should be returned (last in priority)
            wizard = manager.get_class("wizard")
            assert wizard is not None
            assert wizard.name == "Wizard (Homebrew)"
            assert wizard.hit_die == 8

        run_async(run_test())

    def test_fallback_to_earlier_source(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source_srd = MockSource("srd", classes={"wizard": WIZARD_CLASS, "fighter": FIGHTER_CLASS})
        source_homebrew = MockSource("homebrew", classes={"wizard": WIZARD_HOMEBREW})  # No fighter

        async def run_test():
            await manager.load_source(source_srd)
            await manager.load_source(source_homebrew)

            # Fighter only exists in SRD
            fighter = manager.get_class("fighter")
            assert fighter is not None
            assert fighter.name == "Fighter"
            assert fighter.source == "srd-2014"

        run_async(run_test())

    def test_set_priority(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source_srd = MockSource("srd", classes={"wizard": WIZARD_CLASS})
        source_homebrew = MockSource("homebrew", classes={"wizard": WIZARD_HOMEBREW})

        async def run_test():
            await manager.load_source(source_srd)
            await manager.load_source(source_homebrew)

            # Change priority so SRD wins
            manager.set_priority(["homebrew", "srd"])

            wizard = manager.get_class("wizard")
            assert wizard is not None
            assert wizard.name == "Wizard"  # SRD version now wins

        run_async(run_test())

    def test_set_priority_invalid(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource("test")

        async def run_test():
            await manager.load_source(source)

            with pytest.raises(RulebookManagerError) as exc_info:
                manager.set_priority(["test", "nonexistent"])

            assert "must contain exactly the loaded source IDs" in str(exc_info.value)

        run_async(run_test())


class TestQueryMethods:
    """Test all query methods."""

    @pytest.fixture
    def loaded_manager(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource(
            "test",
            classes={"wizard": WIZARD_CLASS, "fighter": FIGHTER_CLASS},
            races={"elf": ELF_RACE},
            spells={"fireball": FIREBALL_SPELL},
        )

        async def setup():
            await manager.load_source(source)
            return manager

        return run_async(setup())

    def test_get_class(self, loaded_manager):
        wizard = loaded_manager.get_class("wizard")
        assert wizard is not None
        assert wizard.name == "Wizard"

    def test_get_class_not_found(self, loaded_manager):
        result = loaded_manager.get_class("nonexistent")
        assert result is None

    def test_get_race(self, loaded_manager):
        elf = loaded_manager.get_race("elf")
        assert elf is not None
        assert elf.name == "Elf"

    def test_get_spell(self, loaded_manager):
        fireball = loaded_manager.get_spell("fireball")
        assert fireball is not None
        assert fireball.name == "Fireball"
        assert fireball.level == 3


class TestSearch:
    """Test search functionality."""

    def test_search_single_source(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource(
            "test",
            classes={"wizard": WIZARD_CLASS, "fighter": FIGHTER_CLASS},
        )

        async def run_test():
            await manager.load_source(source)

            results = manager.search("wizard")
            assert len(results) == 1
            assert results[0].name == "Wizard"
            assert results[0].category == "class"

        run_async(run_test())

    def test_search_multiple_sources(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("srd", classes={"wizard": WIZARD_CLASS})
        source2 = MockSource("homebrew", races={"elf": ELF_RACE})

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)

            # Search for "e" matches Elf and maybe others
            results = manager.search("elf")
            names = [r.name for r in results]
            assert "Elf" in names

        run_async(run_test())

    def test_search_deduplication(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("srd", classes={"wizard": WIZARD_CLASS})
        source2 = MockSource("homebrew", classes={"wizard": WIZARD_HOMEBREW})

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)

            results = manager.search("wizard")
            # Should only return one result (homebrew wins, deduplication)
            assert len(results) == 1
            assert results[0].source == "homebrew"

        run_async(run_test())

    def test_search_with_limit(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        # Create source with many classes
        classes = {f"class-{i}": ClassDefinition(
            index=f"class-{i}",
            name=f"Class {i}",
            hit_die=10,
            saving_throws=["STR", "CON"],
            source="test",
        ) for i in range(10)}
        source = MockSource("test", classes=classes)

        async def run_test():
            await manager.load_source(source)

            results = manager.search("Class", limit=3)
            assert len(results) == 3

        run_async(run_test())


class TestContentCounts:
    """Test content counting."""

    def test_content_counts_single_source(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource(
            "test",
            classes={"wizard": WIZARD_CLASS, "fighter": FIGHTER_CLASS},
            races={"elf": ELF_RACE},
            spells={"fireball": FIREBALL_SPELL},
        )

        async def run_test():
            await manager.load_source(source)

            counts = manager.content_counts()
            assert counts.classes == 2
            assert counts.races == 1
            assert counts.spells == 1

        run_async(run_test())

    def test_content_counts_multiple_sources(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("srd", classes={"wizard": WIZARD_CLASS})
        source2 = MockSource("homebrew", classes={"fighter": FIGHTER_CLASS}, races={"elf": ELF_RACE})

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)

            counts = manager.content_counts()
            assert counts.classes == 2  # Combined
            assert counts.races == 1

        run_async(run_test())

    def test_content_counts_specific_source(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("srd", classes={"wizard": WIZARD_CLASS})
        source2 = MockSource("homebrew", classes={"fighter": FIGHTER_CLASS})

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)

            counts = manager.content_counts("srd")
            assert counts.classes == 1

            counts = manager.content_counts("homebrew")
            assert counts.classes == 1

        run_async(run_test())


class TestManifestPersistence:
    """Test manifest save/load."""

    def test_manifest_created_on_load(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource("test-source")

        async def run_test():
            await manager.load_source(source)

            manifest_path = tmp_path / "rulebooks" / "manifest.json"
            assert manifest_path.exists()

            data = json.loads(manifest_path.read_text())
            assert len(data["active_sources"]) == 1
            assert data["active_sources"][0]["id"] == "test-source"
            assert data["priority"] == ["test-source"]

        run_async(run_test())

    def test_manifest_updated_on_unload(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source1 = MockSource("source-1")
        source2 = MockSource("source-2")

        async def run_test():
            await manager.load_source(source1)
            await manager.load_source(source2)
            manager.unload_source("source-1")

            manifest_path = tmp_path / "rulebooks" / "manifest.json"
            data = json.loads(manifest_path.read_text())

            assert len(data["active_sources"]) == 1
            assert data["active_sources"][0]["id"] == "source-2"

        run_async(run_test())

    def test_no_manifest_without_campaign_dir(self):
        manager = RulebookManager()  # No campaign_dir
        source = MockSource("test")

        async def run_test():
            await manager.load_source(source)
            # Should not raise, just not save

        run_async(run_test())


class TestFactoryMethods:
    """Test factory methods."""

    def test_with_srd(self, tmp_path):
        """Test creating manager with SRD (using mock)."""
        import gamemaster_mcp.rulebooks.sources.srd as srd_module

        async def run_test():
            original_class = srd_module.SRDSource

            mock_source = MagicMock()
            mock_source.source_id = "srd-2014"
            mock_source.is_loaded = False
            mock_source.load = AsyncMock()
            mock_source.source_type = RulebookSource.SRD
            mock_source.version = "2014"
            mock_source.loaded_at = None

            # Patch the class in the module
            srd_module.SRDSource = MagicMock(return_value=mock_source)
            try:
                manager = await RulebookManager.with_srd(campaign_dir=tmp_path)

                assert "srd-2014" in manager.source_ids
                srd_module.SRDSource.assert_called_once_with(version="2014", cache_dir=None)
                mock_source.load.assert_called_once()
            finally:
                srd_module.SRDSource = original_class

        run_async(run_test())

    def test_from_manifest(self, tmp_path):
        """Test loading from manifest."""
        import gamemaster_mcp.rulebooks.sources.srd as srd_module

        # Create a manifest
        manifest_dir = tmp_path / "rulebooks"
        manifest_dir.mkdir(parents=True)
        manifest_path = manifest_dir / "manifest.json"

        manifest_data = {
            "active_sources": [
                {"id": "srd-2014", "type": "srd", "version": "2014", "loaded_at": "2026-01-01T00:00:00Z"}
            ],
            "priority": ["srd-2014"],
            "conflict_resolution": "last_wins",
        }
        manifest_path.write_text(json.dumps(manifest_data))

        async def run_test():
            original_class = srd_module.SRDSource

            mock_source = MagicMock()
            mock_source.source_id = "srd-2014"
            mock_source.is_loaded = False
            mock_source.load = AsyncMock()
            mock_source.source_type = RulebookSource.SRD
            mock_source.version = "2014"
            mock_source.loaded_at = None

            srd_module.SRDSource = MagicMock(return_value=mock_source)
            try:
                manager = await RulebookManager.from_manifest(tmp_path)

                assert "srd-2014" in manager.source_ids
            finally:
                srd_module.SRDSource = original_class

        run_async(run_test())

    def test_from_manifest_not_found(self, tmp_path):
        """Test error when manifest doesn't exist."""

        async def run_test():
            with pytest.raises(RulebookManagerError) as exc_info:
                await RulebookManager.from_manifest(tmp_path)

            assert "No manifest found" in str(exc_info.value)

        run_async(run_test())


class TestCleanup:
    """Test cleanup methods."""

    def test_close(self, tmp_path):
        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource("test")

        async def run_test():
            await manager.load_source(source)
            assert len(manager.sources) == 1

            await manager.close()
            assert len(manager.sources) == 0
            assert len(manager.priority) == 0

        run_async(run_test())


class TestThreadSafety:
    """Test thread-safety of query operations."""

    def test_concurrent_queries(self, tmp_path):
        """Test that concurrent queries don't cause issues."""
        import threading

        manager = RulebookManager(campaign_dir=tmp_path)
        source = MockSource(
            "test",
            classes={"wizard": WIZARD_CLASS},
            races={"elf": ELF_RACE},
        )

        async def setup():
            await manager.load_source(source)

        run_async(setup())

        results = []
        errors = []

        def query_class():
            try:
                for _ in range(100):
                    result = manager.get_class("wizard")
                    if result:
                        results.append(result.name)
            except Exception as e:
                errors.append(e)

        def query_race():
            try:
                for _ in range(100):
                    result = manager.get_race("elf")
                    if result:
                        results.append(result.name)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=query_class),
            threading.Thread(target=query_race),
            threading.Thread(target=query_class),
            threading.Thread(target=query_race),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 400  # 4 threads * 100 queries each
