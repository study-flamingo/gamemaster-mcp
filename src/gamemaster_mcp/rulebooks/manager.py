"""
RulebookManager - Orchestrates multiple rulebook sources.

This module provides the main entry point for all rulebook operations,
managing multiple sources with priority resolution and unified querying.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Iterator

from .models import (
    ClassDefinition,
    SubclassDefinition,
    RaceDefinition,
    SubraceDefinition,
    SpellDefinition,
    MonsterDefinition,
    FeatDefinition,
    BackgroundDefinition,
    ItemDefinition,
    RulebookSource as RulebookSourceEnum,
)
from .sources.base import RulebookSourceBase, SearchResult, ContentCounts

if TYPE_CHECKING:
    from .sources.srd import SRDSource
    from .sources.custom import CustomSource

logger = logging.getLogger(__name__)


class RulebookManagerError(Exception):
    """Exception raised by RulebookManager operations."""
    pass


@dataclass
class SourceConfig:
    """Configuration for a loaded source."""
    id: str
    type: str  # "srd" or "custom"
    loaded_at: str  # ISO timestamp
    version: str | None = None  # For SRD sources
    path: str | None = None  # For custom sources

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "type": self.type,
            "loaded_at": self.loaded_at,
        }
        if self.version:
            result["version"] = self.version
        if self.path:
            result["path"] = self.path
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SourceConfig":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            loaded_at=data["loaded_at"],
            version=data.get("version"),
            path=data.get("path"),
        )


@dataclass
class Manifest:
    """Manifest tracking active sources and configuration."""
    active_sources: list[SourceConfig] = field(default_factory=list)
    priority: list[str] = field(default_factory=list)
    conflict_resolution: str = "last_wins"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "active_sources": [s.to_dict() for s in self.active_sources],
            "priority": self.priority,
            "conflict_resolution": self.conflict_resolution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        """Create from dictionary."""
        return cls(
            active_sources=[SourceConfig.from_dict(s) for s in data.get("active_sources", [])],
            priority=data.get("priority", []),
            conflict_resolution=data.get("conflict_resolution", "last_wins"),
        )


class RulebookManager:
    """
    Orchestrates multiple rulebook sources with unified query interface.

    The manager supports loading multiple sources (SRD, custom rulebooks) and
    provides a unified interface to query content. When the same content exists
    in multiple sources, the priority order determines which one is returned
    (last wins by default).

    Thread-safe for concurrent queries.
    """

    def __init__(self, campaign_dir: Path | None = None):
        """
        Initialize the RulebookManager.

        Args:
            campaign_dir: Directory for campaign data. If provided, manifest is
                         persisted to {campaign_dir}/rulebooks/manifest.json
        """
        self.campaign_dir = campaign_dir
        self._sources: dict[str, RulebookSourceBase] = {}
        self._priority: list[str] = []
        self._lock = RLock()
        self._manifest_dir: Path | None = None

        if campaign_dir:
            self._manifest_dir = campaign_dir / "rulebooks"
            self._manifest_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sources(self) -> dict[str, RulebookSourceBase]:
        """Get loaded sources (read-only view)."""
        with self._lock:
            return dict(self._sources)

    @property
    def priority(self) -> list[str]:
        """Get source priority order (first to last, last wins)."""
        with self._lock:
            return list(self._priority)

    @property
    def source_ids(self) -> list[str]:
        """Get IDs of all loaded sources."""
        with self._lock:
            return list(self._sources.keys())

    def is_loaded(self, source_id: str) -> bool:
        """Check if a source is loaded."""
        with self._lock:
            return source_id in self._sources

    # =========================================================================
    # Source Management
    # =========================================================================

    async def load_source(self, source: RulebookSourceBase) -> None:
        """
        Add and load a rulebook source.

        Args:
            source: The source to load

        Raises:
            RulebookManagerError: If loading fails
        """
        try:
            if not source.is_loaded:
                await source.load()

            with self._lock:
                # Remove existing source with same ID if present
                if source.source_id in self._sources:
                    self._priority.remove(source.source_id)

                self._sources[source.source_id] = source
                self._priority.append(source.source_id)

            self._save_manifest()
            logger.info(f"Loaded source: {source.source_id}")

        except Exception as e:
            raise RulebookManagerError(f"Failed to load source {source.source_id}: {e}") from e

    def unload_source(self, source_id: str) -> bool:
        """
        Remove a source from the manager.

        Args:
            source_id: ID of the source to remove

        Returns:
            True if source was removed, False if not found
        """
        with self._lock:
            if source_id not in self._sources:
                return False

            del self._sources[source_id]
            self._priority.remove(source_id)

        self._save_manifest()
        logger.info(f"Unloaded source: {source_id}")
        return True

    def set_priority(self, priority: list[str]) -> None:
        """
        Set the source priority order.

        Args:
            priority: List of source IDs in priority order (last wins)

        Raises:
            RulebookManagerError: If priority list doesn't match loaded sources
        """
        with self._lock:
            if set(priority) != set(self._sources.keys()):
                raise RulebookManagerError(
                    f"Priority list must contain exactly the loaded source IDs. "
                    f"Expected: {set(self._sources.keys())}, got: {set(priority)}"
                )
            self._priority = list(priority)

        self._save_manifest()

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_class(self, index: str) -> ClassDefinition | None:
        """
        Get a class definition by index.

        Searches sources in reverse priority order (last wins).

        Args:
            index: The class index (e.g., "wizard")

        Returns:
            ClassDefinition if found, None otherwise
        """
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_class(index)
                if result:
                    return result
        return None

    def get_subclass(self, index: str) -> SubclassDefinition | None:
        """Get a subclass definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_subclass(index)
                if result:
                    return result
        return None

    def get_race(self, index: str) -> RaceDefinition | None:
        """Get a race definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_race(index)
                if result:
                    return result
        return None

    def get_subrace(self, index: str) -> SubraceDefinition | None:
        """Get a subrace definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_subrace(index)
                if result:
                    return result
        return None

    def get_spell(self, index: str) -> SpellDefinition | None:
        """Get a spell definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_spell(index)
                if result:
                    return result
        return None

    def get_monster(self, index: str) -> MonsterDefinition | None:
        """Get a monster definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_monster(index)
                if result:
                    return result
        return None

    def get_feat(self, index: str) -> FeatDefinition | None:
        """Get a feat definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_feat(index)
                if result:
                    return result
        return None

    def get_background(self, index: str) -> BackgroundDefinition | None:
        """Get a background definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_background(index)
                if result:
                    return result
        return None

    def get_item(self, index: str) -> ItemDefinition | None:
        """Get an item definition by index."""
        with self._lock:
            for source_id in reversed(self._priority):
                result = self._sources[source_id].get_item(index)
                if result:
                    return result
        return None

    def search(
        self,
        query: str,
        categories: list[str] | None = None,
        limit: int = 20,
        source_id: str | None = None,
    ) -> list[SearchResult]:
        """
        Search across all loaded sources.

        Args:
            query: Search term (case-insensitive, partial match)
            categories: Filter to specific categories (class, race, spell, etc.)
            limit: Maximum number of results
            source_id: If provided, search only in this source

        Returns:
            List of SearchResult objects
        """
        results: list[SearchResult] = []
        seen: set[tuple[str, str]] = set()  # (category, index) for deduplication

        with self._lock:
            # Search in reverse priority order so later sources can override
            sources_to_search = (
                [self._sources[source_id]] if source_id and source_id in self._sources
                else [self._sources[sid] for sid in reversed(self._priority)]
            )

            for source in sources_to_search:
                for result in source.search(query, categories):
                    key = (result.category, result.index)
                    if key not in seen:
                        seen.add(key)
                        results.append(result)

                        if len(results) >= limit:
                            return results

        return results

    def content_counts(self, source_id: str | None = None) -> ContentCounts:
        """
        Get content counts.

        Args:
            source_id: If provided, return counts for specific source only.
                      Otherwise, return combined counts from all sources.

        Returns:
            ContentCounts object
        """
        with self._lock:
            if source_id:
                if source_id in self._sources:
                    return self._sources[source_id].content_counts()
                return ContentCounts()

            # Combine counts from all sources
            total = ContentCounts()
            for source in self._sources.values():
                counts = source.content_counts()
                total.classes += counts.classes
                total.subclasses += counts.subclasses
                total.races += counts.races
                total.subraces += counts.subraces
                total.spells += counts.spells
                total.monsters += counts.monsters
                total.feats += counts.feats
                total.backgrounds += counts.backgrounds
                total.items += counts.items
            return total

    # =========================================================================
    # Manifest Persistence
    # =========================================================================

    def _get_manifest_path(self) -> Path | None:
        """Get path to manifest file."""
        if self._manifest_dir:
            return self._manifest_dir / "manifest.json"
        return None

    def _save_manifest(self) -> None:
        """Save current state to manifest file."""
        manifest_path = self._get_manifest_path()
        if not manifest_path:
            return

        manifest = Manifest(
            active_sources=[self._source_to_config(s) for s in self._sources.values()],
            priority=list(self._priority),
        )

        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))
        logger.debug(f"Saved manifest to {manifest_path}")

    def _load_manifest(self) -> Manifest | None:
        """Load manifest from file."""
        manifest_path = self._get_manifest_path()
        if not manifest_path or not manifest_path.exists():
            return None

        try:
            data = json.loads(manifest_path.read_text())
            return Manifest.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load manifest: {e}")
            return None

    def _source_to_config(self, source: RulebookSourceBase) -> SourceConfig:
        """Convert a source to its config representation."""
        loaded_at = (
            source.loaded_at.isoformat() if source.loaded_at
            else datetime.now(timezone.utc).isoformat()
        )

        if source.source_type == RulebookSourceEnum.SRD:
            # SRD source
            version = getattr(source, "version", "2014")
            return SourceConfig(
                id=source.source_id,
                type="srd",
                loaded_at=loaded_at,
                version=version,
            )
        else:
            # Custom source
            path = getattr(source, "file_path", None)
            return SourceConfig(
                id=source.source_id,
                type="custom",
                loaded_at=loaded_at,
                path=str(path) if path else None,
            )

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    async def with_srd(
        cls,
        campaign_dir: Path | None = None,
        version: str = "2014",
        cache_dir: Path | None = None,
    ) -> "RulebookManager":
        """
        Create a RulebookManager with SRD pre-loaded.

        Args:
            campaign_dir: Optional campaign directory for manifest persistence
            version: SRD version ("2014" or "2024")
            cache_dir: Optional cache directory for SRD data

        Returns:
            Initialized RulebookManager with SRD loaded
        """
        from .sources.srd import SRDSource

        manager = cls(campaign_dir)
        srd_source = SRDSource(version=version, cache_dir=cache_dir)
        await manager.load_source(srd_source)
        return manager

    @classmethod
    async def from_manifest(cls, campaign_dir: Path) -> "RulebookManager":
        """
        Load a RulebookManager from an existing manifest.

        Args:
            campaign_dir: Campaign directory containing manifest

        Returns:
            Initialized RulebookManager with sources from manifest

        Raises:
            RulebookManagerError: If manifest cannot be loaded
        """
        manager = cls(campaign_dir)
        manifest = manager._load_manifest()

        if not manifest:
            raise RulebookManagerError(
                f"No manifest found at {campaign_dir / 'rulebooks' / 'manifest.json'}"
            )

        for source_config in manifest.active_sources:
            source = await manager._create_source_from_config(source_config)
            await manager.load_source(source)

        # Restore priority order
        if manifest.priority:
            manager._priority = manifest.priority

        return manager

    async def _create_source_from_config(self, config: SourceConfig) -> RulebookSourceBase:
        """Create a source instance from its config."""
        if config.type == "srd":
            from .sources.srd import SRDSource

            cache_dir = self._manifest_dir / "cache" if self._manifest_dir else None
            return SRDSource(version=config.version or "2014", cache_dir=cache_dir)

        elif config.type == "custom":
            from .sources.custom import CustomSource

            if not config.path:
                raise RulebookManagerError(f"Custom source {config.id} missing path")
            return CustomSource(Path(config.path), source_id=config.id)

        else:
            raise RulebookManagerError(f"Unknown source type: {config.type}")

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def close(self) -> None:
        """Close all sources and clean up resources."""
        with self._lock:
            for source in self._sources.values():
                await source.close()
            self._sources.clear()
            self._priority.clear()

    def __repr__(self) -> str:
        source_info = ", ".join(self._sources.keys()) if self._sources else "none"
        return f"RulebookManager(sources=[{source_info}])"


__all__ = [
    "RulebookManager",
    "RulebookManagerError",
    "SourceConfig",
    "Manifest",
]
