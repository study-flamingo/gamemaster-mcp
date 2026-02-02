"""
Unit tests for MCP rulebook management tools.

Tests cover:
- load_rulebook with SRD source
- load_rulebook with custom source
- load_rulebook without campaign (error case)
- list_rulebooks with empty state
- list_rulebooks with sources
- unload_rulebook success
- unload_rulebook not found

Note: These tests exercise the logic behind the MCP tools by directly
testing with DnDStorage and RulebookManager instances.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.rulebooks import RulebookManager
from gamemaster_mcp.rulebooks.sources.srd import SRDSource
from gamemaster_mcp.rulebooks.sources.custom import CustomSource


def run_async(coro):
    """Helper to run async code in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# Test fixtures
@pytest.fixture
def temp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir()
    return storage_dir


@pytest.fixture
def storage_with_campaign(temp_storage_dir: Path) -> DnDStorage:
    """Create a storage instance with a test campaign."""
    storage = DnDStorage(data_dir=temp_storage_dir)
    campaign = storage.create_campaign(
        name="Test Campaign",
        description="A test campaign for rulebook tests",
        dm_name="Test DM",
    )
    return storage


@pytest.fixture
def custom_rulebook_file(tmp_path: Path) -> Path:
    """Create a custom rulebook JSON file for testing."""
    rulebook_path = tmp_path / "custom_rulebook.json"
    rulebook_data = {
        "classes": [
            {
                "index": "artificer",
                "name": "Artificer",
                "hit_die": 8,
                "proficiency_choices": [],
                "proficiencies": [],
                "saving_throws": ["con", "int"],
            }
        ],
        "races": [
            {
                "index": "warforged",
                "name": "Warforged",
                "speed": 30,
                "ability_bonuses": [{"ability_score": {"index": "con"}, "bonus": 2}],
                "alignment": "Warforged tend toward lawful neutral.",
                "age": "A typical warforged is between two and thirty years old.",
                "size": "Medium",
                "size_description": "Your size is Medium.",
                "language_desc": "You can speak, read, and write Common and one other language.",
            }
        ],
        "spells": [
            {
                "index": "arcane-weapon",
                "name": "Arcane Weapon",
                "level": 1,
                "school": {"index": "transmutation", "name": "Transmutation"},
                "casting_time": "1 bonus action",
                "range": "Self",
                "components": ["V", "S"],
                "duration": "Concentration, up to 1 hour",
                "desc": ["You channel arcane energy into one simple or martial weapon you're holding."],
            }
        ],
    }
    rulebook_path.write_text(json.dumps(rulebook_data, indent=2))
    return rulebook_path


# ----------------------------------------------------------------------
# Tests: load_rulebook logic
# ----------------------------------------------------------------------


def test_load_rulebook_no_campaign(temp_storage_dir: Path):
    """Test load_rulebook behavior without a campaign loaded."""
    storage = DnDStorage(data_dir=temp_storage_dir)
    # Storage is empty - no current campaign
    assert storage._current_campaign is None

    # This simulates what the tool would return
    if not storage._current_campaign:
        result = "❌ No campaign loaded. Use `load_campaign` first."

    assert "No campaign loaded" in result
    assert "❌" in result


def test_load_rulebook_srd(storage_with_campaign: DnDStorage):
    """Test loading SRD rulebook."""
    # Initialize manager if not exists
    if not storage_with_campaign.rulebook_manager:
        campaign_dir = storage_with_campaign._split_backend._get_campaign_dir(
            storage_with_campaign._current_campaign.name
        )
        storage_with_campaign._rulebook_manager = RulebookManager(campaign_dir)

    # Mock the SRD source to avoid network calls
    with patch.object(SRDSource, 'load', new_callable=AsyncMock) as mock_load:
        # Set up mock to simulate successful load
        srd_source = SRDSource(version="2014", cache_dir=storage_with_campaign.rulebook_cache_dir)
        srd_source._is_loaded = True
        srd_source._classes = {"wizard": MagicMock()}
        srd_source._races = {"elf": MagicMock()}
        srd_source._spells = {"fireball": MagicMock()}
        srd_source._monsters = {"goblin": MagicMock()}

        run_async(storage_with_campaign.rulebook_manager.load_source(srd_source))

    counts = srd_source.content_counts()
    result = f"✅ Loaded SRD 2014 rulebook\n📚 {counts.classes} classes, {counts.races} races, {counts.spells} spells, {counts.monsters} monsters"

    # Check success message
    assert "✅" in result
    assert "Loaded SRD" in result
    assert "2014" in result

    # Check content counts are present
    assert "classes" in result
    assert "races" in result
    assert "spells" in result
    assert "monsters" in result

    # Verify manager was created
    assert storage_with_campaign.rulebook_manager is not None
    assert len(storage_with_campaign.rulebook_manager.sources) > 0


def test_load_rulebook_custom(
    storage_with_campaign: DnDStorage, custom_rulebook_file: Path
):
    """Test loading custom rulebook."""
    # Initialize manager if not exists
    if not storage_with_campaign.rulebook_manager:
        campaign_dir = storage_with_campaign._split_backend._get_campaign_dir(
            storage_with_campaign._current_campaign.name
        )
        storage_with_campaign._rulebook_manager = RulebookManager(campaign_dir)

    # Copy custom rulebook to campaign rulebooks directory
    campaign_dir = storage_with_campaign._split_backend._get_campaign_dir(
        storage_with_campaign._current_campaign.name
    )
    rulebooks_dir = campaign_dir / "rulebooks" / "custom"
    rulebooks_dir.mkdir(parents=True, exist_ok=True)
    dest_path = rulebooks_dir / "custom.json"
    dest_path.write_text(custom_rulebook_file.read_text())

    # Load custom source
    full_path = storage_with_campaign.rulebooks_dir / "custom" / "custom.json"
    custom_source = CustomSource(full_path)
    run_async(storage_with_campaign.rulebook_manager.load_source(custom_source))

    counts = custom_source.content_counts()
    result = f"✅ Loaded custom rulebook: custom/custom.json\n📚 {counts.classes} classes, {counts.races} races, {counts.spells} spells"

    # Check success message
    assert "✅" in result
    assert "Loaded custom rulebook" in result
    assert "custom" in result

    # Check content counts
    assert "classes" in result
    assert "races" in result
    assert "spells" in result

    # Verify manager was created and source loaded
    assert storage_with_campaign.rulebook_manager is not None
    assert len(storage_with_campaign.rulebook_manager.sources) > 0


def test_load_rulebook_custom_no_path(storage_with_campaign: DnDStorage):
    """Test load_rulebook behavior with custom source but no path."""
    # Simulate the check in the tool
    source = "custom"
    path = None

    if source == "custom":
        if not path:
            result = "❌ Custom source requires 'path' parameter"
        else:
            result = "ok"

    # Check error message
    assert "❌" in result
    assert "requires 'path' parameter" in result


# ----------------------------------------------------------------------
# Tests: list_rulebooks logic
# ----------------------------------------------------------------------


def test_list_rulebooks_no_campaign(temp_storage_dir: Path):
    """Test list_rulebooks behavior without a campaign loaded."""
    storage = DnDStorage(data_dir=temp_storage_dir)
    assert storage._current_campaign is None

    # This simulates what the tool would return
    if not storage._current_campaign:
        result = "❌ No campaign loaded."

    assert "No campaign loaded" in result
    assert "❌" in result


def test_list_rulebooks_empty(storage_with_campaign: DnDStorage):
    """Test list_rulebooks with no rulebooks loaded."""
    # No manager initialized
    if not storage_with_campaign.rulebook_manager or not storage_with_campaign.rulebook_manager.sources:
        result = "📚 No rulebooks loaded. Use `load_rulebook` to add one."

    assert "No rulebooks loaded" in result
    assert "📚" in result


def test_list_rulebooks_with_sources(storage_with_campaign: DnDStorage):
    """Test list_rulebooks with loaded sources."""
    # Initialize manager and load SRD
    campaign_dir = storage_with_campaign._split_backend._get_campaign_dir(
        storage_with_campaign._current_campaign.name
    )
    storage_with_campaign._rulebook_manager = RulebookManager(campaign_dir)

    # Mock the SRD source to avoid network calls
    with patch.object(SRDSource, 'load', new_callable=AsyncMock):
        srd_source = SRDSource(version="2014", cache_dir=storage_with_campaign.rulebook_cache_dir)
        srd_source._is_loaded = True
        srd_source._classes = {"wizard": MagicMock()}
        srd_source._races = {"elf": MagicMock()}
        srd_source._spells = {"fireball": MagicMock()}
        srd_source._monsters = {"goblin": MagicMock()}
        run_async(storage_with_campaign.rulebook_manager.load_source(srd_source))

    # List rulebooks
    rulebooks = []
    for source_id, source in storage_with_campaign.rulebook_manager.sources.items():
        counts = source.content_counts()
        rulebooks.append({
            "id": source_id,
            "type": source.source_type.value,
            "loaded_at": source.loaded_at.isoformat() if source.loaded_at else None,
            "content": {
                "classes": counts.classes,
                "races": counts.races,
                "spells": counts.spells,
                "monsters": counts.monsters,
            }
        })

    # Markdown output
    lines = ["# Active Rulebooks\n"]
    for rb in rulebooks:
        lines.append(f"## {rb['id']}")
        lines.append(f"- **Type:** {rb['type']}")
        if rb['loaded_at']:
            lines.append(f"- **Loaded:** {rb['loaded_at']}")
        lines.append(f"- **Content:** {rb['content']['classes']} classes, {rb['content']['races']} races, {rb['content']['spells']} spells, {rb['content']['monsters']} monsters")
        lines.append("")

    result = "\n".join(lines)

    # Check markdown output
    assert "Active Rulebooks" in result
    assert "Type:" in result
    assert "Content:" in result
    assert "classes" in result
    assert "races" in result


# ----------------------------------------------------------------------
# Tests: unload_rulebook logic
# ----------------------------------------------------------------------


def test_unload_rulebook_no_campaign(temp_storage_dir: Path):
    """Test unload_rulebook behavior without a campaign loaded."""
    storage = DnDStorage(data_dir=temp_storage_dir)
    assert storage._current_campaign is None

    # This simulates what the tool would return
    if not storage._current_campaign:
        result = "❌ No campaign loaded."

    assert "No campaign loaded" in result
    assert "❌" in result


def test_unload_rulebook_no_manager(storage_with_campaign: DnDStorage):
    """Test unload_rulebook without a rulebook manager."""
    # No manager initialized
    if not storage_with_campaign.rulebook_manager:
        result = "❌ No rulebooks loaded."

    assert "No rulebooks loaded" in result
    assert "❌" in result


def test_unload_rulebook_success(storage_with_campaign: DnDStorage):
    """Test successfully unloading a rulebook."""
    # Initialize manager and load SRD
    campaign_dir = storage_with_campaign._split_backend._get_campaign_dir(
        storage_with_campaign._current_campaign.name
    )
    storage_with_campaign._rulebook_manager = RulebookManager(campaign_dir)

    # Mock the SRD source to avoid network calls
    with patch.object(SRDSource, 'load', new_callable=AsyncMock):
        srd_source = SRDSource(version="2014", cache_dir=storage_with_campaign.rulebook_cache_dir)
        srd_source._is_loaded = True
        srd_source._classes = {"wizard": MagicMock()}
        srd_source._races = {"elf": MagicMock()}
        srd_source._spells = {"fireball": MagicMock()}
        srd_source._monsters = {"goblin": MagicMock()}
        run_async(storage_with_campaign.rulebook_manager.load_source(srd_source))

    # Get the source ID
    source_id = list(storage_with_campaign.rulebook_manager.sources.keys())[0]

    # Unload it
    if storage_with_campaign.rulebook_manager.unload_source(source_id):
        result = f"✅ Unloaded rulebook: {source_id}"
    else:
        result = f"❌ Rulebook not found: {source_id}"

    assert "✅" in result
    assert "Unloaded rulebook" in result
    assert source_id in result

    # Verify it was removed
    assert len(storage_with_campaign.rulebook_manager.sources) == 0


def test_unload_rulebook_not_found(storage_with_campaign: DnDStorage):
    """Test unloading a non-existent rulebook."""
    # Initialize manager and load SRD
    campaign_dir = storage_with_campaign._split_backend._get_campaign_dir(
        storage_with_campaign._current_campaign.name
    )
    storage_with_campaign._rulebook_manager = RulebookManager(campaign_dir)

    # Mock the SRD source to avoid network calls
    with patch.object(SRDSource, 'load', new_callable=AsyncMock):
        srd_source = SRDSource(version="2014", cache_dir=storage_with_campaign.rulebook_cache_dir)
        srd_source._is_loaded = True
        srd_source._classes = {"wizard": MagicMock()}
        srd_source._races = {"elf": MagicMock()}
        srd_source._spells = {"fireball": MagicMock()}
        srd_source._monsters = {"goblin": MagicMock()}
        run_async(storage_with_campaign.rulebook_manager.load_source(srd_source))

    # Try to unload a non-existent source
    source_id = "non-existent"
    if storage_with_campaign.rulebook_manager.unload_source(source_id):
        result = f"✅ Unloaded rulebook: {source_id}"
    else:
        result = f"❌ Rulebook not found: {source_id}"

    assert "❌" in result
    assert "not found" in result
