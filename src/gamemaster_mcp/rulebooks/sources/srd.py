"""
SRD API client for loading official D&D 5e System Reference Document content.

This source fetches data from the 5e-srd-api (https://www.dnd5eapi.co/) and
caches responses locally for offline use and performance.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import httpx

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
    ClassLevelInfo,
    SpellcastingInfo,
    AbilityBonus,
    RacialTrait,
    ArmorClassInfo,
    MonsterAbility,
    MonsterAction,
    BackgroundFeature,
    Prerequisite,
    RulebookSource as RulebookSourceType,
    SpellSchool,
    Size,
)
from .base import RulebookSourceBase, SearchResult, ContentCounts


logger = logging.getLogger("gamemaster-mcp")


# API Configuration
SRD_API_BASE = "https://www.dnd5eapi.co/api"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


class SRDSourceError(Exception):
    """Error fetching or parsing SRD data."""
    pass


class SRDSource(RulebookSourceBase):
    """
    Rulebook source for the official D&D 5e SRD via 5e-srd-api.

    Features:
    - Fetches classes, races, spells, monsters, and more
    - Caches all responses locally for offline use
    - Handles rate limits with exponential backoff
    - Supports both 2014 and 2024 SRD versions (when available)
    """

    def __init__(
        self,
        version: str = "2014",
        cache_dir: Path | None = None,
    ):
        """
        Initialize the SRD source.

        Args:
            version: SRD version ("2014" or "2024")
            cache_dir: Directory for caching API responses
        """
        source_id = f"srd-{version}"
        super().__init__(
            source_id=source_id,
            source_type=RulebookSourceType.SRD,
            name=f"D&D 5e SRD ({version})",
        )

        self.version = version
        self.cache_dir = cache_dir or Path("dnd_data/rulebook_cache") / f"srd_{version}"
        self._client: httpx.AsyncClient | None = None

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
        """Load all SRD content from API or cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            self._client = client

            try:
                # Load content in batches to manage concurrency
                await self._load_classes()
                await self._load_races()
                await self._load_spells()
                await self._load_monsters()
                await self._load_equipment()
                await self._load_feats()
                await self._load_backgrounds()

            finally:
                self._client = None

        self._loaded = True
        self.loaded_at = datetime.now()

        logger.info(f"Loaded SRD {self.version}: {self.stats_summary()}")

    async def close(self) -> None:
        """Close HTTP client if open."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # HTTP Helpers
    # =========================================================================

    async def _fetch(self, endpoint: str) -> dict[str, Any]:
        """
        Fetch from API with caching and retry logic.

        Args:
            endpoint: API endpoint (e.g., "/classes/wizard")

        Returns:
            Parsed JSON response

        Raises:
            SRDSourceError: If fetch fails after retries
        """
        # Check cache first
        cache_file = self._get_cache_path(endpoint)
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logger.warning(f"Corrupt cache file: {cache_file}, refetching")
                cache_file.unlink()

        # Fetch from API with retry
        # API requires version in path: /api/2014/classes or /api/2024/classes
        url = f"{SRD_API_BASE}/{self.version}{endpoint}"
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.get(url)

                if response.status_code == 429:
                    # Rate limited
                    wait = RETRY_BACKOFF ** attempt
                    logger.warning(f"Rate limited, waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

                # Cache the response
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

                return data

            except httpx.TimeoutException as e:
                logger.warning(f"Timeout fetching {endpoint}, attempt {attempt + 1}")
                last_error = e
                await asyncio.sleep(RETRY_BACKOFF ** attempt)

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"Server error {e.response.status_code}, attempt {attempt + 1}")
                    last_error = e
                    await asyncio.sleep(RETRY_BACKOFF ** attempt)
                else:
                    raise SRDSourceError(f"HTTP error: {e}") from e

        raise SRDSourceError(f"Failed to fetch {endpoint} after {MAX_RETRIES} retries: {last_error}")

    def _get_cache_path(self, endpoint: str) -> Path:
        """Convert endpoint to cache file path."""
        # /classes/wizard -> classes_wizard.json
        safe_name = endpoint.strip("/").replace("/", "_")
        return self.cache_dir / f"{safe_name}.json"

    async def _fetch_list(self, endpoint: str) -> list[dict[str, Any]]:
        """Fetch a list endpoint and return the results array."""
        data = await self._fetch(endpoint)
        return data.get("results", [])

    # =========================================================================
    # Content Loading
    # =========================================================================

    async def _load_classes(self) -> None:
        """Load all classes and their subclasses."""
        class_list = await self._fetch_list("/classes")

        for class_ref in class_list:
            index = class_ref["index"]
            try:
                # Fetch class details
                class_data = await self._fetch(f"/classes/{index}")

                # Fetch level progression
                levels_data = await self._fetch(f"/classes/{index}/levels")

                # Map to our model
                class_def = self._map_class(class_data, levels_data)
                self._classes[index] = class_def

                # Load subclasses
                for subclass_ref in class_data.get("subclasses", []):
                    sub_index = subclass_ref["index"]
                    try:
                        sub_data = await self._fetch(f"/subclasses/{sub_index}")
                        sub_def = self._map_subclass(sub_data)
                        self._subclasses[sub_index] = sub_def
                    except Exception as e:
                        logger.warning(f"Failed to load subclass {sub_index}: {e}")

            except Exception as e:
                logger.warning(f"Failed to load class {index}: {e}")

    async def _load_races(self) -> None:
        """Load all races and subraces."""
        race_list = await self._fetch_list("/races")

        for race_ref in race_list:
            index = race_ref["index"]
            try:
                race_data = await self._fetch(f"/races/{index}")
                race_def = self._map_race(race_data)
                self._races[index] = race_def

                # Load subraces
                for subrace_ref in race_data.get("subraces", []):
                    sub_index = subrace_ref["index"]
                    try:
                        sub_data = await self._fetch(f"/subraces/{sub_index}")
                        sub_def = self._map_subrace(sub_data)
                        self._subraces[sub_index] = sub_def
                    except Exception as e:
                        logger.warning(f"Failed to load subrace {sub_index}: {e}")

            except Exception as e:
                logger.warning(f"Failed to load race {index}: {e}")

    async def _load_spells(self) -> None:
        """Load all spells."""
        spell_list = await self._fetch_list("/spells")

        # Load spells in batches to avoid overwhelming the API
        batch_size = 20
        for i in range(0, len(spell_list), batch_size):
            batch = spell_list[i:i + batch_size]
            tasks = [self._load_spell(ref["index"]) for ref in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _load_spell(self, index: str) -> None:
        """Load a single spell."""
        try:
            spell_data = await self._fetch(f"/spells/{index}")
            spell_def = self._map_spell(spell_data)
            self._spells[index] = spell_def
        except Exception as e:
            logger.warning(f"Failed to load spell {index}: {e}")

    async def _load_monsters(self) -> None:
        """Load all monsters."""
        monster_list = await self._fetch_list("/monsters")

        # Load monsters in batches
        batch_size = 20
        for i in range(0, len(monster_list), batch_size):
            batch = monster_list[i:i + batch_size]
            tasks = [self._load_monster(ref["index"]) for ref in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _load_monster(self, index: str) -> None:
        """Load a single monster."""
        try:
            monster_data = await self._fetch(f"/monsters/{index}")
            monster_def = self._map_monster(monster_data)
            self._monsters[index] = monster_def
        except Exception as e:
            logger.warning(f"Failed to load monster {index}: {e}")

    async def _load_equipment(self) -> None:
        """Load equipment/items."""
        equipment_list = await self._fetch_list("/equipment")

        batch_size = 20
        for i in range(0, len(equipment_list), batch_size):
            batch = equipment_list[i:i + batch_size]
            tasks = [self._load_item(ref["index"]) for ref in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _load_item(self, index: str) -> None:
        """Load a single item."""
        try:
            item_data = await self._fetch(f"/equipment/{index}")
            item_def = self._map_item(item_data)
            self._items[index] = item_def
        except Exception as e:
            logger.warning(f"Failed to load item {index}: {e}")

    async def _load_feats(self) -> None:
        """Load all feats."""
        feat_list = await self._fetch_list("/feats")

        for feat_ref in feat_list:
            index = feat_ref["index"]
            try:
                feat_data = await self._fetch(f"/feats/{index}")
                feat_def = self._map_feat(feat_data)
                self._feats[index] = feat_def
            except Exception as e:
                logger.warning(f"Failed to load feat {index}: {e}")

    async def _load_backgrounds(self) -> None:
        """Load all backgrounds."""
        bg_list = await self._fetch_list("/backgrounds")

        for bg_ref in bg_list:
            index = bg_ref["index"]
            try:
                bg_data = await self._fetch(f"/backgrounds/{index}")
                bg_def = self._map_background(bg_data)
                self._backgrounds[index] = bg_def
            except Exception as e:
                logger.warning(f"Failed to load background {index}: {e}")

    # =========================================================================
    # Data Mapping
    # =========================================================================

    def _map_class(self, data: dict, levels_data: list[dict]) -> ClassDefinition:
        """Map API class data to ClassDefinition."""
        # Build level info
        class_levels: dict[int, ClassLevelInfo] = {}
        for level_data in levels_data:
            level = level_data.get("level", 1)
            features = [f["name"] for f in level_data.get("features", [])]
            class_levels[level] = ClassLevelInfo(
                level=level,
                proficiency_bonus=level_data.get("prof_bonus", 2),
                features=features,
                class_specific=level_data.get("class_specific", {}),
            )

        # Build spellcasting info if applicable
        spellcasting = None
        if data.get("spellcasting"):
            sc = data["spellcasting"]
            spellcasting = SpellcastingInfo(
                level=sc.get("level", 1),
                spellcasting_ability=sc.get("spellcasting_ability", {}).get("index", "").upper(),
            )

        return ClassDefinition(
            index=data["index"],
            name=data["name"],
            hit_die=data.get("hit_die", 8),
            proficiencies=[p["name"] for p in data.get("proficiencies", [])],
            saving_throws=[st["name"] for st in data.get("saving_throws", [])],
            starting_equipment=[e.get("equipment", {}).get("name", "") for e in data.get("starting_equipment", [])],
            spellcasting=spellcasting,
            class_levels=class_levels,
            subclasses=[s["index"] for s in data.get("subclasses", [])],
            source=self.source_id,
        )

    def _map_subclass(self, data: dict) -> SubclassDefinition:
        """Map API subclass data to SubclassDefinition."""
        return SubclassDefinition(
            index=data["index"],
            name=data["name"],
            parent_class=data.get("class", {}).get("index", ""),
            subclass_flavor=data.get("subclass_flavor"),
            desc=data.get("desc", []),
            source=self.source_id,
        )

    def _map_race(self, data: dict) -> RaceDefinition:
        """Map API race data to RaceDefinition."""
        # Map ability bonuses
        ability_bonuses = []
        for ab in data.get("ability_bonuses", []):
            ability_bonuses.append(AbilityBonus(
                ability_score=ab.get("ability_score", {}).get("index", "").upper(),
                bonus=ab.get("bonus", 0),
            ))

        # Map traits
        traits = []
        for t in data.get("traits", []):
            traits.append(RacialTrait(
                index=t.get("index", ""),
                name=t.get("name", ""),
            ))

        # Map size
        size_str = data.get("size", "Medium")
        try:
            size = Size(size_str)
        except ValueError:
            size = Size.MEDIUM

        return RaceDefinition(
            index=data["index"],
            name=data["name"],
            speed=data.get("speed", 30),
            ability_bonuses=ability_bonuses,
            size=size,
            languages=[l["name"] for l in data.get("languages", [])],
            traits=traits,
            subraces=[s["index"] for s in data.get("subraces", [])],
            source=self.source_id,
        )

    def _map_subrace(self, data: dict) -> SubraceDefinition:
        """Map API subrace data to SubraceDefinition."""
        ability_bonuses = []
        for ab in data.get("ability_bonuses", []):
            ability_bonuses.append(AbilityBonus(
                ability_score=ab.get("ability_score", {}).get("index", "").upper(),
                bonus=ab.get("bonus", 0),
            ))

        return SubraceDefinition(
            index=data["index"],
            name=data["name"],
            parent_race=data.get("race", {}).get("index", ""),
            ability_bonuses=ability_bonuses,
            source=self.source_id,
        )

    def _map_spell(self, data: dict) -> SpellDefinition:
        """Map API spell data to SpellDefinition."""
        # Map school
        school_str = data.get("school", {}).get("name", "Evocation")
        try:
            school = SpellSchool(school_str)
        except ValueError:
            school = SpellSchool.EVOCATION

        # Map components
        components = data.get("components", [])

        return SpellDefinition(
            index=data["index"],
            name=data["name"],
            level=data.get("level", 0),
            school=school,
            casting_time=data.get("casting_time", "1 action"),
            range=data.get("range", "Self"),
            duration=data.get("duration", "Instantaneous"),
            components=components,
            material=data.get("material"),
            ritual=data.get("ritual", False),
            concentration=data.get("concentration", False),
            desc=data.get("desc", []),
            higher_level=data.get("higher_level"),
            classes=[c["index"] for c in data.get("classes", [])],
            subclasses=[s["index"] for s in data.get("subclasses", [])],
            damage_type=data.get("damage", {}).get("damage_type", {}).get("name"),
            source=self.source_id,
        )

    def _map_monster(self, data: dict) -> MonsterDefinition:
        """Map API monster data to MonsterDefinition."""
        # Map size
        size_str = data.get("size", "Medium")
        try:
            size = Size(size_str)
        except ValueError:
            size = Size.MEDIUM

        # Map armor class
        armor_class = []
        for ac in data.get("armor_class", [{"type": "natural", "value": 10}]):
            armor_class.append(ArmorClassInfo(
                type=ac.get("type", "natural"),
                value=ac.get("value", 10),
            ))

        # Map special abilities
        special_abilities = []
        for ability in data.get("special_abilities", []):
            special_abilities.append(MonsterAbility(
                name=ability.get("name", ""),
                desc=ability.get("desc", ""),
                usage=ability.get("usage"),
                dc=ability.get("dc"),
            ))

        # Map actions
        actions = []
        for action in data.get("actions", []):
            actions.append(MonsterAction(
                name=action.get("name", ""),
                desc=action.get("desc", ""),
                attack_bonus=action.get("attack_bonus"),
                damage=action.get("damage"),
                dc=action.get("dc"),
            ))

        # Map legendary actions
        legendary_actions = None
        if data.get("legendary_actions"):
            legendary_actions = []
            for la in data["legendary_actions"]:
                legendary_actions.append(MonsterAction(
                    name=la.get("name", ""),
                    desc=la.get("desc", ""),
                ))

        return MonsterDefinition(
            index=data["index"],
            name=data["name"],
            size=size,
            type=data.get("type", ""),
            subtype=data.get("subtype"),
            alignment=data.get("alignment", ""),
            armor_class=armor_class,
            hit_points=data.get("hit_points", 1),
            hit_dice=data.get("hit_dice", "1d8"),
            speed=data.get("speed", {}),
            strength=data.get("strength", 10),
            dexterity=data.get("dexterity", 10),
            constitution=data.get("constitution", 10),
            intelligence=data.get("intelligence", 10),
            wisdom=data.get("wisdom", 10),
            charisma=data.get("charisma", 10),
            proficiencies=data.get("proficiencies", []),
            damage_vulnerabilities=data.get("damage_vulnerabilities", []),
            damage_resistances=data.get("damage_resistances", []),
            damage_immunities=data.get("damage_immunities", []),
            condition_immunities=[c.get("name", "") for c in data.get("condition_immunities", [])],
            senses=data.get("senses", {}),
            languages=data.get("languages", ""),
            challenge_rating=data.get("challenge_rating", 0),
            xp=data.get("xp", 0),
            special_abilities=special_abilities,
            actions=actions,
            legendary_actions=legendary_actions,
            source=self.source_id,
        )

    def _map_feat(self, data: dict) -> FeatDefinition:
        """Map API feat data to FeatDefinition."""
        prerequisites = []
        for prereq in data.get("prerequisites", []):
            prerequisites.append(Prerequisite(
                type=prereq.get("type", ""),
                ability_score=prereq.get("ability_score", {}).get("index"),
                minimum_score=prereq.get("minimum_score"),
            ))

        return FeatDefinition(
            index=data["index"],
            name=data["name"],
            desc=data.get("desc", []),
            prerequisites=prerequisites,
            source=self.source_id,
        )

    def _map_background(self, data: dict) -> BackgroundDefinition:
        """Map API background data to BackgroundDefinition."""
        feature = None
        if data.get("feature"):
            feature = BackgroundFeature(
                name=data["feature"].get("name", ""),
                desc=data["feature"].get("desc", []),
            )

        return BackgroundDefinition(
            index=data["index"],
            name=data["name"],
            starting_proficiencies=[p["name"] for p in data.get("starting_proficiencies", [])],
            feature=feature,
            source=self.source_id,
        )

    def _map_item(self, data: dict) -> ItemDefinition:
        """Map API equipment data to ItemDefinition."""
        return ItemDefinition(
            index=data["index"],
            name=data["name"],
            desc=data.get("desc", []),
            equipment_category=data.get("equipment_category", {}).get("index", "gear"),
            cost=data.get("cost"),
            weight=data.get("weight"),
            weapon_category=data.get("weapon_category"),
            weapon_range=data.get("weapon_range"),
            damage=data.get("damage"),
            properties=[p["name"] for p in data.get("properties", [])],
            armor_category=data.get("armor_category"),
            armor_class=data.get("armor_class"),
            source=self.source_id,
        )

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
        """Search across all SRD content."""
        query_lower = query.lower()
        count = 0

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

        if categories:
            search_categories = [(k, v) for k, v in category_map.items() if k in categories]
        else:
            search_categories = list(category_map.items())

        for category_name, (storage, cat) in search_categories:
            for index, item in storage.items():
                if count >= limit:
                    return

                if query_lower in index or query_lower in item.name.lower():
                    yield SearchResult(
                        index=item.index,
                        name=item.name,
                        category=cat,  # type: ignore
                        source=self.source_id,
                        summary=getattr(item, "desc", [None])[0] if hasattr(item, "desc") and item.desc else None,
                    )
                    count += 1

    def content_counts(self) -> ContentCounts:
        """Get counts of all SRD content."""
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
    "SRDSource",
    "SRDSourceError",
]
