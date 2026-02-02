"""
Abstract base class for rulebook data sources.

This module defines the interface that all rulebook sources must implement,
enabling a plugin architecture for different data sources (SRD API, Open5e, local files).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterator, Literal

from ..models import (
    ClassDefinition,
    SubclassDefinition,
    RaceDefinition,
    SubraceDefinition,
    SpellDefinition,
    MonsterDefinition,
    FeatDefinition,
    BackgroundDefinition,
    ItemDefinition,
    RulebookSource as RulebookSourceType,
)


@dataclass
class SearchResult:
    """Result from a search query."""
    index: str
    name: str
    category: Literal["class", "subclass", "race", "subrace", "spell", "monster", "feat", "background", "item"]
    source: str
    summary: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "name": self.name,
            "category": self.category,
            "source": self.source,
            "summary": self.summary,
        }


@dataclass
class ContentCounts:
    """Counts of content in a source."""
    classes: int = 0
    subclasses: int = 0
    races: int = 0
    subraces: int = 0
    spells: int = 0
    monsters: int = 0
    feats: int = 0
    backgrounds: int = 0
    items: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "classes": self.classes,
            "subclasses": self.subclasses,
            "races": self.races,
            "subraces": self.subraces,
            "spells": self.spells,
            "monsters": self.monsters,
            "feats": self.feats,
            "backgrounds": self.backgrounds,
            "items": self.items,
        }

    def __str__(self) -> str:
        """Return formatted summary."""
        non_empty = {k: v for k, v in self.to_dict().items() if v > 0}
        if not non_empty:
            return "empty"
        return ", ".join(f"{v} {k}" for k, v in non_empty.items())


class RulebookSourceBase(ABC):
    """
    Abstract base class for rulebook data sources.

    All rulebook sources (SRD API, Open5e, custom files) must implement this interface.
    This enables a unified query mechanism regardless of where the data comes from.
    """

    def __init__(
        self,
        source_id: str,
        source_type: RulebookSourceType,
        name: str | None = None,
    ):
        """
        Initialize the source.

        Args:
            source_id: Unique identifier for this source instance (e.g., "srd-2014", "homebrew-races")
            source_type: Type of source (srd, open5e, custom)
            name: Human-readable name for the source
        """
        self.source_id = source_id
        self.source_type = source_type
        self.name = name or source_id
        self.loaded_at: datetime | None = None
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if the source has been loaded."""
        return self._loaded

    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    async def load(self) -> None:
        """
        Load or refresh data from the source.

        This method should:
        - Fetch/read all content from the source
        - Parse and validate the content
        - Store it in internal structures for querying
        - Set self._loaded = True and self.loaded_at on success

        Raises:
            Exception: If loading fails
        """
        pass

    @abstractmethod
    def get_class(self, index: str) -> ClassDefinition | None:
        """
        Get a class definition by its index.

        Args:
            index: The class index (e.g., "wizard", "fighter")

        Returns:
            ClassDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_subclass(self, index: str) -> SubclassDefinition | None:
        """
        Get a subclass definition by its index.

        Args:
            index: The subclass index (e.g., "evocation", "champion")

        Returns:
            SubclassDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_race(self, index: str) -> RaceDefinition | None:
        """
        Get a race definition by its index.

        Args:
            index: The race index (e.g., "elf", "dwarf")

        Returns:
            RaceDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_subrace(self, index: str) -> SubraceDefinition | None:
        """
        Get a subrace definition by its index.

        Args:
            index: The subrace index (e.g., "high-elf", "hill-dwarf")

        Returns:
            SubraceDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_spell(self, index: str) -> SpellDefinition | None:
        """
        Get a spell definition by its index.

        Args:
            index: The spell index (e.g., "fireball", "cure-wounds")

        Returns:
            SpellDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_monster(self, index: str) -> MonsterDefinition | None:
        """
        Get a monster definition by its index.

        Args:
            index: The monster index (e.g., "goblin", "adult-red-dragon")

        Returns:
            MonsterDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_feat(self, index: str) -> FeatDefinition | None:
        """
        Get a feat definition by its index.

        Args:
            index: The feat index (e.g., "alert", "lucky")

        Returns:
            FeatDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_background(self, index: str) -> BackgroundDefinition | None:
        """
        Get a background definition by its index.

        Args:
            index: The background index (e.g., "soldier", "sage")

        Returns:
            BackgroundDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def get_item(self, index: str) -> ItemDefinition | None:
        """
        Get an item definition by its index.

        Args:
            index: The item index (e.g., "longsword", "bag-of-holding")

        Returns:
            ItemDefinition if found, None otherwise
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        categories: list[str] | None = None,
        limit: int = 20,
    ) -> Iterator[SearchResult]:
        """
        Search across all content in this source.

        Args:
            query: Search term (case-insensitive, partial match)
            categories: Filter to specific categories (class, race, spell, monster, etc.)
                       If None, search all categories
            limit: Maximum number of results to return

        Yields:
            SearchResult objects matching the query
        """
        pass

    @abstractmethod
    def content_counts(self) -> ContentCounts:
        """
        Get counts of all content types in this source.

        Returns:
            ContentCounts with counts for each category
        """
        pass

    # =========================================================================
    # Optional Methods - Can be overridden by subclasses
    # =========================================================================

    def stats_summary(self) -> str:
        """
        Get a formatted summary of content counts.

        Returns:
            String like "12 classes, 50 spells, 100 monsters"
        """
        return str(self.content_counts())

    async def close(self) -> None:
        """
        Clean up any resources (e.g., HTTP connections).

        Override this if your source needs cleanup.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.source_id!r}, type={self.source_type.value!r})"


__all__ = [
    "RulebookSourceBase",
    "SearchResult",
    "ContentCounts",
]
