"""
Custom rulebook source for loading local JSON/YAML files.

This source allows users to define homebrew content in structured files
that integrate seamlessly with official SRD content.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import yaml
from pydantic import ValidationError

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
from .base import RulebookSourceBase, SearchResult, ContentCounts


logger = logging.getLogger("gamemaster-mcp")


class CustomSourceError(Exception):
    """Error loading or parsing a custom rulebook."""
    pass


class CustomSource(RulebookSourceBase):
    """
    Rulebook source for loading local JSON or YAML files.

    Supports partial rulebooks (e.g., a file with only custom races)
    and provides schema validation for content.

    File formats supported:
    - .json - JSON files
    - .yaml / .yml - YAML files

    Expected file structure:
    ```json
    {
      "$schema": "gamemaster-mcp/rulebook-v1",
      "name": "My Homebrew",
      "version": "1.0",
      "content": {
        "classes": [...],
        "races": [...],
        "spells": [...],
        ...
      }
    }
    ```
    """

    SUPPORTED_EXTENSIONS = {".json", ".yaml", ".yml"}
    CURRENT_SCHEMA = "gamemaster-mcp/rulebook-v1"

    def __init__(
        self,
        path: Path | str,
        source_id: str | None = None,
    ):
        """
        Initialize a custom source from a file path.

        Args:
            path: Path to the JSON or YAML file
            source_id: Optional custom ID. If not provided, derived from filename.
        """
        self.path = Path(path)

        if source_id is None:
            # Derive source_id from filename: "my_races.json" -> "custom-my-races"
            source_id = f"custom-{self.path.stem.replace('_', '-').lower()}"

        super().__init__(
            source_id=source_id,
            source_type=RulebookSourceType.CUSTOM,
            name=None,  # Will be set from file content
        )

        # Content storage
        self._classes: dict[str, ClassDefinition] = {}
        self._subclasses: dict[str, SubclassDefinition] = {}
        self._races: dict[str, RaceDefinition] = {}
        self._subraces: dict[str, SubraceDefinition] = {}
        self._spells: dict[str, SpellDefinition] = {}
        self._monsters: dict[str, MonsterDefinition] = {}
        self._feats: dict[str, FeatDefinition] = {}
        self._backgrounds: dict[str, BackgroundDefinition] = {}
        self._items: dict[str, ItemDefinition] = {}

    async def load(self) -> None:
        """Load and parse the rulebook file."""
        if not self.path.exists():
            raise CustomSourceError(f"Rulebook file not found: {self.path}")

        suffix = self.path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            raise CustomSourceError(
                f"Unsupported file format: {suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        try:
            raw_content = self.path.read_text(encoding="utf-8")
        except OSError as e:
            raise CustomSourceError(f"Failed to read file: {e}") from e

        try:
            if suffix == ".json":
                data = json.loads(raw_content)
            else:  # .yaml or .yml
                data = yaml.safe_load(raw_content)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise CustomSourceError(f"Failed to parse {suffix} file: {e}") from e

        if not isinstance(data, dict):
            raise CustomSourceError("Rulebook must be a JSON/YAML object at the top level")

        # Validate schema if present
        schema = data.get("$schema")
        if schema and schema != self.CURRENT_SCHEMA:
            logger.warning(
                f"Rulebook schema '{schema}' differs from current '{self.CURRENT_SCHEMA}'. "
                "Some features may not work correctly."
            )

        # Extract metadata
        self.name = data.get("name", self.source_id)
        self._version = data.get("version", "1.0")

        # Parse content
        content = data.get("content", data)  # Support both nested and flat structure

        self._parse_content(content)

        self._loaded = True
        self.loaded_at = datetime.now()

        logger.info(f"Loaded custom rulebook '{self.name}' from {self.path}: {self.stats_summary()}")

    def _parse_content(self, content: dict[str, Any]) -> None:
        """Parse all content sections from the rulebook."""
        # Classes
        for item in content.get("classes", []):
            try:
                cls = self._parse_class(item)
                self._classes[cls.index] = cls
            except ValidationError as e:
                logger.warning(f"Invalid class definition in {self.path}: {e}")

        # Subclasses
        for item in content.get("subclasses", []):
            try:
                subcls = self._parse_subclass(item)
                self._subclasses[subcls.index] = subcls
            except ValidationError as e:
                logger.warning(f"Invalid subclass definition in {self.path}: {e}")

        # Races
        for item in content.get("races", []):
            try:
                race = self._parse_race(item)
                self._races[race.index] = race
            except ValidationError as e:
                logger.warning(f"Invalid race definition in {self.path}: {e}")

        # Subraces
        for item in content.get("subraces", []):
            try:
                subrace = self._parse_subrace(item)
                self._subraces[subrace.index] = subrace
            except ValidationError as e:
                logger.warning(f"Invalid subrace definition in {self.path}: {e}")

        # Spells
        for item in content.get("spells", []):
            try:
                spell = self._parse_spell(item)
                self._spells[spell.index] = spell
            except ValidationError as e:
                logger.warning(f"Invalid spell definition in {self.path}: {e}")

        # Monsters
        for item in content.get("monsters", []):
            try:
                monster = self._parse_monster(item)
                self._monsters[monster.index] = monster
            except ValidationError as e:
                logger.warning(f"Invalid monster definition in {self.path}: {e}")

        # Feats
        for item in content.get("feats", []):
            try:
                feat = self._parse_feat(item)
                self._feats[feat.index] = feat
            except ValidationError as e:
                logger.warning(f"Invalid feat definition in {self.path}: {e}")

        # Backgrounds
        for item in content.get("backgrounds", []):
            try:
                bg = self._parse_background(item)
                self._backgrounds[bg.index] = bg
            except ValidationError as e:
                logger.warning(f"Invalid background definition in {self.path}: {e}")

        # Items
        for item in content.get("items", []):
            try:
                itm = self._parse_item(item)
                self._items[itm.index] = itm
            except ValidationError as e:
                logger.warning(f"Invalid item definition in {self.path}: {e}")

    def _ensure_index(self, data: dict, name_field: str = "name") -> dict:
        """Ensure the data has an index field, deriving from name if needed."""
        if "index" not in data:
            name = data.get(name_field, "unknown")
            data["index"] = name.lower().replace(" ", "-").replace("'", "")
        return data

    def _ensure_source(self, data: dict) -> dict:
        """Ensure the data has source field set to this source."""
        data["source"] = self.source_id
        return data

    def _parse_class(self, data: dict) -> ClassDefinition:
        """Parse a class definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return ClassDefinition.model_validate(data)

    def _parse_subclass(self, data: dict) -> SubclassDefinition:
        """Parse a subclass definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return SubclassDefinition.model_validate(data)

    def _parse_race(self, data: dict) -> RaceDefinition:
        """Parse a race definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return RaceDefinition.model_validate(data)

    def _parse_subrace(self, data: dict) -> SubraceDefinition:
        """Parse a subrace definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return SubraceDefinition.model_validate(data)

    def _parse_spell(self, data: dict) -> SpellDefinition:
        """Parse a spell definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return SpellDefinition.model_validate(data)

    def _parse_monster(self, data: dict) -> MonsterDefinition:
        """Parse a monster definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return MonsterDefinition.model_validate(data)

    def _parse_feat(self, data: dict) -> FeatDefinition:
        """Parse a feat definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return FeatDefinition.model_validate(data)

    def _parse_background(self, data: dict) -> BackgroundDefinition:
        """Parse a background definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return BackgroundDefinition.model_validate(data)

    def _parse_item(self, data: dict) -> ItemDefinition:
        """Parse an item definition."""
        data = self._ensure_index(data)
        data = self._ensure_source(data)
        return ItemDefinition.model_validate(data)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_class(self, index: str) -> ClassDefinition | None:
        return self._classes.get(index.lower())

    def get_subclass(self, index: str) -> SubclassDefinition | None:
        return self._subclasses.get(index.lower())

    def get_race(self, index: str) -> RaceDefinition | None:
        return self._races.get(index.lower())

    def get_subrace(self, index: str) -> SubraceDefinition | None:
        return self._subraces.get(index.lower())

    def get_spell(self, index: str) -> SpellDefinition | None:
        return self._spells.get(index.lower())

    def get_monster(self, index: str) -> MonsterDefinition | None:
        return self._monsters.get(index.lower())

    def get_feat(self, index: str) -> FeatDefinition | None:
        return self._feats.get(index.lower())

    def get_background(self, index: str) -> BackgroundDefinition | None:
        return self._backgrounds.get(index.lower())

    def get_item(self, index: str) -> ItemDefinition | None:
        return self._items.get(index.lower())

    def search(
        self,
        query: str,
        categories: list[str] | None = None,
        limit: int = 20,
    ) -> Iterator[SearchResult]:
        """Search across all content."""
        query_lower = query.lower()
        count = 0

        # Define category -> (storage, category_name) mapping
        category_map = {
            "class": (self._classes, "class"),
            "subclass": (self._subclasses, "subclass"),
            "race": (self._races, "race"),
            "subrace": (self._subraces, "subrace"),
            "spell": (self._spells, "spell"),
            "monster": (self._monsters, "monster"),
            "feat": (self._feats, "feat"),
            "background": (self._backgrounds, "background"),
            "item": (self._items, "item"),
        }

        # Filter to requested categories
        if categories:
            search_categories = [(k, v) for k, v in category_map.items() if k in categories]
        else:
            search_categories = list(category_map.items())

        for category_name, (storage, cat) in search_categories:
            for index, item in storage.items():
                if count >= limit:
                    return

                # Match on index or name
                if query_lower in index or query_lower in item.name.lower():
                    yield SearchResult(
                        index=item.index,
                        name=item.name,
                        category=cat,  # type: ignore
                        source=self.source_id,
                        summary=getattr(item, "desc", [None])[0] if hasattr(item, "desc") else None,
                    )
                    count += 1

    def content_counts(self) -> ContentCounts:
        """Get counts of all content types."""
        return ContentCounts(
            classes=len(self._classes),
            subclasses=len(self._subclasses),
            races=len(self._races),
            subraces=len(self._subraces),
            spells=len(self._spells),
            monsters=len(self._monsters),
            feats=len(self._feats),
            backgrounds=len(self._backgrounds),
            items=len(self._items),
        )


__all__ = [
    "CustomSource",
    "CustomSourceError",
]
