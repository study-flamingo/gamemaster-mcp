"""
Tests for rulebook data models.
"""

import pytest
from datetime import datetime

from gamemaster_mcp.rulebooks.models import (
    # Enums
    RulebookSource,
    Size,
    SpellSchool,
    ItemRarity,
    # Classes
    ClassDefinition,
    SubclassDefinition,
    ClassLevelInfo,
    SpellcastingInfo,
    # Races
    RaceDefinition,
    SubraceDefinition,
    AbilityBonus,
    RacialTrait,
    # Spells
    SpellDefinition,
    # Monsters
    MonsterDefinition,
    MonsterAbility,
    MonsterAction,
    ArmorClassInfo,
    # Other
    FeatDefinition,
    BackgroundDefinition,
    BackgroundFeature,
    ItemDefinition,
    Prerequisite,
    # Containers
    Rulebook,
    RulebookManifest,
    RulebookManifestEntry,
)


class TestEnums:
    """Test enum definitions."""

    def test_rulebook_source_values(self):
        assert RulebookSource.SRD == "srd"
        assert RulebookSource.OPEN5E == "open5e"
        assert RulebookSource.CUSTOM == "custom"

    def test_size_values(self):
        assert Size.TINY == "Tiny"
        assert Size.MEDIUM == "Medium"
        assert Size.GARGANTUAN == "Gargantuan"

    def test_spell_school_values(self):
        assert SpellSchool.EVOCATION == "Evocation"
        assert SpellSchool.NECROMANCY == "Necromancy"

    def test_item_rarity_values(self):
        assert ItemRarity.COMMON == "Common"
        assert ItemRarity.LEGENDARY == "Legendary"


class TestClassDefinition:
    """Test ClassDefinition model."""

    def test_minimal_class(self):
        cls = ClassDefinition(
            index="fighter",
            name="Fighter",
            hit_die=10,
            saving_throws=["STR", "CON"],
        )
        assert cls.index == "fighter"
        assert cls.name == "Fighter"
        assert cls.hit_die == 10
        assert cls.source == "srd"  # default
        assert cls.subclass_level == 3  # default

    def test_full_class(self):
        cls = ClassDefinition(
            index="wizard",
            name="Wizard",
            hit_die=6,
            saving_throws=["INT", "WIS"],
            proficiencies=["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
            spellcasting=SpellcastingInfo(
                level=1,
                spellcasting_ability="INT",
                caster_type="full",
            ),
            subclasses=["evocation", "divination"],
            subclass_level=2,
            source="srd-2014",
        )
        assert cls.spellcasting is not None
        assert cls.spellcasting.spellcasting_ability == "INT"
        assert len(cls.subclasses) == 2

    def test_class_level_info(self):
        level_info = ClassLevelInfo(
            level=5,
            proficiency_bonus=3,
            features=["Extra Attack"],
            class_specific={"attacks_per_action": 2},
        )
        assert level_info.level == 5
        assert level_info.proficiency_bonus == 3
        assert "Extra Attack" in level_info.features


class TestRaceDefinition:
    """Test RaceDefinition model."""

    def test_minimal_race(self):
        race = RaceDefinition(
            index="human",
            name="Human",
            speed=30,
            languages=["Common"],
        )
        assert race.speed == 30
        assert race.size == Size.MEDIUM  # default
        assert "Common" in race.languages

    def test_race_with_bonuses(self):
        race = RaceDefinition(
            index="dwarf",
            name="Dwarf",
            speed=25,
            ability_bonuses=[AbilityBonus(ability_score="CON", bonus=2)],
            size=Size.MEDIUM,
            traits=[
                RacialTrait(
                    index="darkvision",
                    name="Darkvision",
                    desc=["You can see in dim light within 60 feet."],
                )
            ],
            languages=["Common", "Dwarvish"],
            subraces=["hill-dwarf", "mountain-dwarf"],
        )
        assert race.ability_bonuses[0].bonus == 2
        assert len(race.traits) == 1
        assert len(race.subraces) == 2

    def test_subrace(self):
        subrace = SubraceDefinition(
            index="high-elf",
            name="High Elf",
            parent_race="elf",
            ability_bonuses=[AbilityBonus(ability_score="INT", bonus=1)],
        )
        assert subrace.parent_race == "elf"


class TestSpellDefinition:
    """Test SpellDefinition model."""

    def test_cantrip(self):
        spell = SpellDefinition(
            index="fire-bolt",
            name="Fire Bolt",
            level=0,
            school=SpellSchool.EVOCATION,
            casting_time="1 action",
            range="120 feet",
            duration="Instantaneous",
            components=["V", "S"],
            classes=["wizard", "sorcerer"],
        )
        assert spell.level == 0
        assert spell.level_text == "Cantrip"
        assert not spell.ritual
        assert not spell.concentration

    def test_leveled_spell(self):
        spell = SpellDefinition(
            index="fireball",
            name="Fireball",
            level=3,
            school=SpellSchool.EVOCATION,
            casting_time="1 action",
            range="150 feet",
            duration="Instantaneous",
            components=["V", "S", "M"],
            material="A tiny ball of bat guano and sulfur",
            desc=["A bright streak flashes from your pointing finger..."],
            higher_level=["When cast at 4th level or higher..."],
            damage_type="fire",
        )
        assert spell.level_text == "3rd-level"
        assert spell.material is not None
        assert spell.higher_level is not None

    def test_level_text_ordinals(self):
        """Test ordinal formatting for spell levels."""
        tests = [
            (0, "Cantrip"),
            (1, "1st-level"),
            (2, "2nd-level"),
            (3, "3rd-level"),
            (4, "4th-level"),
            (9, "9th-level"),
        ]
        for level, expected in tests:
            spell = SpellDefinition(
                index=f"test-{level}",
                name=f"Test {level}",
                level=level,
                school=SpellSchool.ABJURATION,
                casting_time="1 action",
                range="Self",
                duration="Instantaneous",
                components=["V"],
            )
            assert spell.level_text == expected


class TestMonsterDefinition:
    """Test MonsterDefinition model."""

    def test_minimal_monster(self):
        monster = MonsterDefinition(
            index="goblin",
            name="Goblin",
            size=Size.SMALL,
            type="humanoid",
            alignment="neutral evil",
            armor_class=[ArmorClassInfo(type="armor", value=15)],
            hit_points=7,
            hit_dice="2d6",
            speed={"walk": "30 ft."},
            strength=8,
            dexterity=14,
            constitution=10,
            intelligence=10,
            wisdom=8,
            charisma=8,
            challenge_rating=0.25,
            xp=50,
        )
        assert monster.size == Size.SMALL
        assert monster.hit_points == 7
        assert monster.challenge_rating == 0.25

    def test_ability_modifier(self):
        monster = MonsterDefinition(
            index="test",
            name="Test",
            size=Size.MEDIUM,
            type="humanoid",
            alignment="neutral",
            armor_class=[ArmorClassInfo(type="natural", value=10)],
            hit_points=10,
            hit_dice="2d8",
            speed={"walk": "30 ft."},
            strength=16,  # +3
            dexterity=14,  # +2
            constitution=12,  # +1
            intelligence=10,  # +0
            wisdom=8,  # -1
            charisma=6,  # -2
            challenge_rating=1,
            xp=200,
        )
        assert monster.get_ability_modifier("strength") == 3
        assert monster.get_ability_modifier("dexterity") == 2
        assert monster.get_ability_modifier("constitution") == 1
        assert monster.get_ability_modifier("intelligence") == 0
        assert monster.get_ability_modifier("wisdom") == -1
        assert monster.get_ability_modifier("charisma") == -2

    def test_monster_with_abilities(self):
        monster = MonsterDefinition(
            index="dragon",
            name="Adult Red Dragon",
            size=Size.HUGE,
            type="dragon",
            alignment="chaotic evil",
            armor_class=[ArmorClassInfo(type="natural", value=19)],
            hit_points=256,
            hit_dice="19d12+133",
            speed={"walk": "40 ft.", "climb": "40 ft.", "fly": "80 ft."},
            strength=27,
            dexterity=10,
            constitution=25,
            intelligence=16,
            wisdom=13,
            charisma=21,
            challenge_rating=17,
            xp=18000,
            damage_immunities=["fire"],
            legendary_actions=[
                MonsterAction(name="Detect", desc="The dragon makes a Wisdom (Perception) check."),
                MonsterAction(name="Tail Attack", desc="The dragon makes a tail attack."),
            ],
        )
        assert monster.size == Size.HUGE
        assert "fire" in monster.damage_immunities
        assert monster.legendary_actions is not None
        assert len(monster.legendary_actions) == 2


class TestFeatDefinition:
    """Test FeatDefinition model."""

    def test_feat_without_prerequisites(self):
        feat = FeatDefinition(
            index="alert",
            name="Alert",
            desc=["Always on the lookout for danger..."],
        )
        assert feat.name == "Alert"
        assert len(feat.prerequisites) == 0

    def test_feat_with_prerequisites(self):
        feat = FeatDefinition(
            index="heavily-armored",
            name="Heavily Armored",
            desc=["You have trained to master the use of heavy armor..."],
            prerequisites=[
                Prerequisite(type="proficiency", proficiency="medium-armor")
            ],
            ability_score_increase=[AbilityBonus(ability_score="STR", bonus=1)],
            proficiencies=["heavy-armor"],
        )
        assert len(feat.prerequisites) == 1
        assert feat.ability_score_increase is not None


class TestBackgroundDefinition:
    """Test BackgroundDefinition model."""

    def test_background(self):
        bg = BackgroundDefinition(
            index="soldier",
            name="Soldier",
            desc=["War has been your life..."],
            starting_proficiencies=["Athletics", "Intimidation"],
            feature=BackgroundFeature(
                name="Military Rank",
                desc=["You have a military rank from your career as a soldier."],
            ),
        )
        assert bg.name == "Soldier"
        assert bg.feature is not None
        assert bg.feature.name == "Military Rank"


class TestItemDefinition:
    """Test ItemDefinition model."""

    def test_weapon(self):
        item = ItemDefinition(
            index="longsword",
            name="Longsword",
            equipment_category="weapon",
            weapon_category="martial",
            damage={"damage_dice": "1d8", "damage_type": "slashing"},
            properties=["versatile"],
            cost={"quantity": 15, "unit": "gp"},
            weight=3,
        )
        assert item.equipment_category == "weapon"
        assert item.damage is not None
        assert "versatile" in item.properties

    def test_magic_item(self):
        item = ItemDefinition(
            index="bag-of-holding",
            name="Bag of Holding",
            desc=["This bag has an interior space considerably larger than its outside dimensions..."],
            equipment_category="wondrous-item",
            rarity=ItemRarity.UNCOMMON,
            requires_attunement=False,
        )
        assert item.rarity == ItemRarity.UNCOMMON
        assert not item.requires_attunement


class TestRulebook:
    """Test Rulebook container model."""

    def test_empty_rulebook(self):
        rb = Rulebook(
            id="test",
            name="Test Rulebook",
            source=RulebookSource.CUSTOM,
        )
        assert rb.content_counts == {
            "classes": 0,
            "subclasses": 0,
            "races": 0,
            "subraces": 0,
            "spells": 0,
            "monsters": 0,
            "feats": 0,
            "backgrounds": 0,
            "items": 0,
        }
        assert rb.stats_summary() == ""

    def test_rulebook_with_content(self):
        rb = Rulebook(
            id="srd-2014",
            name="SRD 2014",
            source=RulebookSource.SRD,
            version="2014",
            classes={
                "wizard": ClassDefinition(
                    index="wizard",
                    name="Wizard",
                    hit_die=6,
                    saving_throws=["INT", "WIS"],
                )
            },
            spells={
                "fireball": SpellDefinition(
                    index="fireball",
                    name="Fireball",
                    level=3,
                    school=SpellSchool.EVOCATION,
                    casting_time="1 action",
                    range="150 feet",
                    duration="Instantaneous",
                    components=["V", "S", "M"],
                )
            },
        )
        assert rb.content_counts["classes"] == 1
        assert rb.content_counts["spells"] == 1
        assert "1 classes" in rb.stats_summary()
        assert "1 spells" in rb.stats_summary()

    def test_rulebook_json_serialization(self):
        rb = Rulebook(
            id="test",
            name="Test",
            source=RulebookSource.CUSTOM,
        )
        json_data = rb.model_dump_json()
        assert "test" in json_data
        assert "custom" in json_data

        # Deserialize
        rb2 = Rulebook.model_validate_json(json_data)
        assert rb2.id == rb.id
        assert rb2.source == rb.source


class TestRulebookManifest:
    """Test RulebookManifest model."""

    def test_empty_manifest(self):
        manifest = RulebookManifest()
        assert len(manifest.active_rulebooks) == 0
        assert manifest.conflict_resolution == "last_wins"

    def test_manifest_with_entries(self):
        manifest = RulebookManifest(
            active_rulebooks=[
                RulebookManifestEntry(
                    id="srd-2014",
                    source=RulebookSource.SRD,
                    version="2014",
                    loaded_at=datetime.now(),
                ),
                RulebookManifestEntry(
                    id="homebrew",
                    source=RulebookSource.CUSTOM,
                    path="custom/homebrew.json",
                    loaded_at=datetime.now(),
                ),
            ],
            priority=["srd-2014", "homebrew"],
        )
        assert len(manifest.active_rulebooks) == 2
        assert manifest.priority == ["srd-2014", "homebrew"]
