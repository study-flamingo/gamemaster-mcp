"""
D&D MCP Server
A comprehensive D&D campaign management server built with modern FastMCP framework.
"""

import logging
import random
import re
import os
from pathlib import Path
from typing import Annotated, Literal
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import Field

from .storage import DnDStorage
from .models import (
    Character, NPC, Location, Quest, SessionNote, AdventureEvent, EventType,
    AbilityScore, CharacterClass, Race, Item
)
from .toon_encoder import encode_to_toon

logger = logging.getLogger("gamemaster-mcp")

logging.basicConfig(
    level=logging.DEBUG,
    )

if not load_dotenv():
    logger.warning("❌ .env file invalid or not found! Please see README.md for instructions. Using project root instead.")

data_path = Path(os.getenv("GAMEMASTER_STORAGE_DIR", "")).resolve()
logger.debug(f"📂 Data path: {data_path}")


# Initialize storage and FastMCP server
storage = DnDStorage(data_dir=data_path)
logger.debug("✅ Storage layer initialized")

mcp = FastMCP(
    name="gamemaster-mcp"
)
logger.debug("✅ Server initialized, registering tools")



# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------

# Campaign management tools
@mcp.tool
def create_campaign(
    name: Annotated[str, Field(description="Campaign name")],
    description: Annotated[str, Field(description="Brief decription of the campaign, or a tagline")],
    dm_name: Annotated[str | None, Field(description="Dungeon Master name")] = None,
    setting: Annotated[str | Path | None, Field(description="""
        Campaign setting - a full description of the setting of the campaign in markdown format, or the path to a `.txt` or `.md` file containing the same.
        """)] = None,
) -> str:
    """Create a new D&D campaign."""
    campaign = storage.create_campaign(
        name=name,
        description=description,
        dm_name=dm_name,
        setting=setting
    )
    return f"🌟 Created campaign: '{campaign.name} and set as active 🌟'"

@mcp.tool
def get_campaign_info(
    format: Annotated[Literal["json", "toon"], Field(description="Output format: 'json' (default) or 'toon' for compact representation")] = "json"
) -> str:
    """Get information about the current campaign.

    Returns campaign information including name, description, counts of various entities,
    and current game state. Supports TOON format for more compact output (~30% token reduction).
    """
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    info = {
        "name": campaign.name,
        "description": campaign.description,
        "dm_name": campaign.dm_name,
        "setting": campaign.get_setting(),
        "character_count": len(campaign.characters),
        "npc_count": len(campaign.npcs),
        "location_count": len(campaign.locations),
        "quest_count": len(campaign.quests),
        "session_count": len(campaign.sessions),
        "current_session": campaign.game_state.current_session,
        "current_location": campaign.game_state.current_location,
        "party_level": campaign.game_state.party_level,
        "in_combat": campaign.game_state.in_combat
    }

    if format == "toon":
        return encode_to_toon(info)

    return f"**Campaign: {campaign.name}**\n\n" + \
           "\n".join([f"**{k.replace('_', ' ').title()}:** {v}" for k, v in info.items()])

@mcp.tool
def list_campaigns() -> str:
    """List all available campaigns."""
    campaigns = storage.list_campaigns()
    if not campaigns:
        return f"❌ No campaigns found in {storage.data_dir}!"

    current = storage.get_current_campaign()
    current_name = current.name if current else None

    campaign_list = []
    for campaign in campaigns:
        marker = " (current)" if campaign == current_name else ""
        campaign_list.append(f"• {campaign}{marker}")

    return "**Available Campaigns:**\n" + "\n".join(campaign_list)

@mcp.tool
def load_campaign(
    name: Annotated[str, Field(description="Campaign name to load")]
) -> str:
    """Load a specific campaign."""
    campaign = storage.load_campaign(name)
    return f"📖 Loaded campaign: '{campaign.name}'. Campaign is now active!"

# Character Management Tools
@mcp.tool
def create_character(
    name: Annotated[str, Field(description="Character name")],
    character_class: Annotated[str, Field(description="Character class")],
    class_level: Annotated[int, Field(description="Class level", ge=1, le=20)],
    race: Annotated[str, Field(description="Character race")],
    player_name: Annotated[str | None, Field(description="The name of the player in control of this character")] = None,
    description: Annotated[str | None, Field(description="A brief description of the character's appearance and demeanor.")] = None,
    bio: Annotated[str | None, Field(description="The character's backstory, personality, and motivations.")] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
    dexterity: Annotated[int, Field(description="Dexterity score", ge=1, le=30)] = 10,
    constitution: Annotated[int, Field(description="Constitution score", ge=1, le=30)] = 10,
    intelligence: Annotated[int, Field(description="Intelligence score", ge=1, le=30)] = 10,
    wisdom: Annotated[int, Field(description="Wisdom score", ge=1, le=30)] = 10,
    charisma: Annotated[int, Field(description="Charisma score", ge=1, le=30)] = 10,
) -> str:
    """Create a new player character."""
    # Build ability scores
    abilities = {
        "strength": AbilityScore(score=strength),
        "dexterity": AbilityScore(score=dexterity),
        "constitution": AbilityScore(score=constitution),
        "intelligence": AbilityScore(score=intelligence),
        "wisdom": AbilityScore(score=wisdom),
        "charisma": AbilityScore(score=charisma),
    }

    character = Character(
        name=name,
        player_name=player_name,
        character_class=CharacterClass(name=character_class, level=class_level),
        race=Race(name=race),
        background=background,
        alignment=alignment,
        abilities=abilities,
        description=description,
        bio=bio,
    )

    storage.add_character(character)
    return f"Created character '{character.name}' (Level {character.character_class.level} {character.race.name} {character.character_class.name})"

@mcp.tool
def get_character(
    name_or_id: Annotated[str, Field(description="Character name, ID, or player name")]
) -> str:
    """Get detailed character information. Accepts character name, ID, or player name."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    char_info = f"""**{character.name}** (`{character.id}`)
Level {character.character_class.level} {character.race.name} {character.character_class.name}
**Player:** {character.player_name or 'N/A'}
**Background:** {character.background or 'N/A'}
**Alignment:** {character.alignment or 'N/A'}

**Description:** {character.description or 'No description provided.'}
**Bio:** {character.bio or 'No bio provided.'}

**Ability Scores:**
• STR: {character.abilities['strength'].score} ({character.abilities['strength'].mod:+d})
• DEX: {character.abilities['dexterity'].score} ({character.abilities['dexterity'].mod:+d})
• CON: {character.abilities['constitution'].score} ({character.abilities['constitution'].mod:+d})
• INT: {character.abilities['intelligence'].score} ({character.abilities['intelligence'].mod:+d})
• WIS: {character.abilities['wisdom'].score} ({character.abilities['wisdom'].mod:+d})
• CHA: {character.abilities['charisma'].score} ({character.abilities['charisma'].mod:+d})

**Combat Stats:**
• AC: {character.armor_class}
• HP: {character.hit_points_current}/{character.hit_points_max}
• Temp HP: {character.temporary_hit_points}

**Inventory:** {len(character.inventory)} items
"""

    return char_info

@mcp.tool
def update_character(
    name_or_id: Annotated[str, Field(description="Character name, ID, or player name.")],
    name: Annotated[str | None, Field(description="New character name. If you change this, you must use the character's ID to identify them.")] = None,
    player_name: Annotated[str | None, Field(description="The name of the player in control of this character")] = None,
    description: Annotated[str | None, Field(description="A brief description of the character's appearance and demeanor.")] = None,
    bio: Annotated[str | None, Field(description="The character's backstory, personality, and motivations.")] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    hit_points_current: Annotated[int | None, Field(description="Current hit points", ge=0)] = None,
    hit_points_max: Annotated[int | None, Field(description="Maximum hit points", ge=1)] = None,
    temporary_hit_points: Annotated[int | None, Field(description="Temporary hit points", ge=0)] = None,
    armor_class: Annotated[int | None, Field(description="Armor class")] = None,
    inspiration: Annotated[bool | None, Field(description="Inspiration status")] = None,
    notes: Annotated[str | None, Field(description="Additional notes about the character")] = None,
    strength: Annotated[int | None, Field(description="Strength score", ge=1, le=30)] = None,
    dexterity: Annotated[int | None, Field(description="Dexterity score", ge=1, le=30)] = None,
    constitution: Annotated[int | None, Field(description="Constitution score", ge=1, le=30)] = None,
    intelligence: Annotated[int | None, Field(description="Intelligence score", ge=1, le=30)] = None,
    wisdom: Annotated[int | None, Field(description="Wisdom score", ge=1, le=30)] = None,
    charisma: Annotated[int | None, Field(description="Charisma score", ge=1, le=30)] = None,
) -> str:
    """Update a character's properties."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    updates = {k: v for k, v in locals().items() if v is not None and k not in ["name_or_id", "character"]}
    updated_fields = [f"{key.replace('_', ' ')}: {value}" for key, value in updates.items()]

    if not updates:
        return f"No updates provided for {character.name}."

    storage.update_character(str(character.id), **updates)

    return f"Updated {character.name}'s properties: {'; '.join(updated_fields)}."

@mcp.tool
def bulk_update_characters(
    names_or_ids: Annotated[list[str], Field(description="List of character names, IDs, or player names to update.")],
    hp_change: Annotated[int | None, Field(description="Amount to change current HP by (positive or negative).")] = None,
    temp_hp_change: Annotated[int | None, Field(description="Amount to change temporary HP by (positive or negative).")] = None,
    strength_change: Annotated[int | None, Field(description="Amount to change strength by.")] = None,
    dexterity_change: Annotated[int | None, Field(description="Amount to change dexterity by.")] = None,
    constitution_change: Annotated[int | None, Field(description="Amount to change constitution by.")] = None,
    intelligence_change: Annotated[int | None, Field(description="Amount to change intelligence by.")] = None,
    wisdom_change: Annotated[int | None, Field(description="Amount to change wisdom by.")] = None,
    charisma_change: Annotated[int | None, Field(description="Amount to change charisma by.")] = None,
) -> str:
    """Update properties for multiple characters at once by a given amount."""
    updates_log = []
    not_found_log = []

    changes = {
        "hp_change": hp_change,
        "temp_hp_change": temp_hp_change,
        "strength_change": strength_change,
        "dexterity_change": dexterity_change,
        "constitution_change": constitution_change,
        "intelligence_change": intelligence_change,
        "wisdom_change": wisdom_change,
        "charisma_change": charisma_change,
    }

    # Filter out None changes
    active_changes = {k: v for k, v in changes.items() if v is not None}
    if not active_changes:
        return "No changes specified."

    # Use batch mode for single save at the end instead of N saves
    with storage.batch_update():
        for name_or_id in names_or_ids:
            character = storage.get_character(name_or_id)
            if not character:
                not_found_log.append(name_or_id)
                continue

            char_updates = {}
            char_log = [f"{character.name}:"]

            if hp_change is not None:
                new_hp = character.hit_points_current + hp_change
                # Clamp HP between 0 and max HP
                new_hp = max(0, min(new_hp, character.hit_points_max))
                char_updates['hit_points_current'] = new_hp
                char_log.append(f"HP -> {new_hp}")

            if temp_hp_change is not None:
                new_temp_hp = character.temporary_hit_points + temp_hp_change
                # Temp HP cannot be negative
                new_temp_hp = max(0, new_temp_hp)
                char_updates['temporary_hit_points'] = new_temp_hp
                char_log.append(f"Temp HP -> {new_temp_hp}")

            abilities_updated = False
            ability_changes = {
                "strength": strength_change, "dexterity": dexterity_change,
                "constitution": constitution_change, "intelligence": intelligence_change,
                "wisdom": wisdom_change, "charisma": charisma_change
            }
            for ability, change in ability_changes.items():
                if change is not None:
                    new_score = character.abilities[ability].score + change
                    new_score = max(1, min(new_score, 30)) # Clamp score
                    character.abilities[ability].score = new_score
                    abilities_updated = True
                    char_log.append(f"{ability.capitalize()} -> {new_score}")

            if abilities_updated:
                char_updates['abilities'] = character.abilities

            if char_updates:
                storage.update_character(str(character.id), **char_updates)
                updates_log.append(" ".join(char_log))
    # Single save happens here when exiting batch_update context

    response_parts = []
    if updates_log:
        response_parts.append("Characters updated:\n" + "\n".join(updates_log))
    if not_found_log:
        response_parts.append(f"Characters not found: {', '.join(not_found_log)}")

    return "\n".join(response_parts) if response_parts else "No characters found to update."

@mcp.tool
def add_item_to_character(
    character_name_or_id: Annotated[str, Field(description="Character name, ID, or player name.")],
    item_name: Annotated[str, Field(description="Item name")],
    description: Annotated[str | None, Field(description="Item description")] = None,
    quantity: Annotated[int, Field(description="Quantity", ge=1)] = 1,
    item_type: Annotated[Literal["weapon", "armor", "consumable", "misc"], Field(description="Item type")] = "misc",
    weight: Annotated[float | None, Field(description="Item weight", ge=0)] = None,
    value: Annotated[str | None, Field(description="Item value (e.g., '50 gp')")] = None,
) -> str:
    """Add an item to a character's inventory."""
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    item = Item(
        name=item_name,
        description=description,
        quantity=quantity,
        item_type=item_type,
        weight=weight,
        value=value
    )

    character.inventory.append(item)
    storage.update_character(str(character.id), inventory=character.inventory)

    return f"Added {item.quantity}x {item.name} to {character.name}'s inventory"

@mcp.tool
def list_characters(
    format: Annotated[Literal["json", "toon"], Field(description="Output format: 'json' (default) or 'toon' for compact representation")] = "json"
) -> str:
    """List all characters in the current campaign.

    Returns a list of all player characters with their basic information.
    Supports TOON format for more compact output (~30% token reduction).
    """
    characters = storage.list_characters_detailed()  # O(n) instead of O(2n)
    if not characters:
        return "No characters in the current campaign."

    if format == "toon":
        # Convert Character objects to dictionaries for TOON encoding
        char_data = [char.model_dump() for char in characters]
        return encode_to_toon(char_data)

    char_list = [
        f"• {char.name} (Level {char.character_class.level} {char.race.name} {char.character_class.name})"
        for char in characters
    ]

    return "**Characters:**\n" + "\n".join(char_list)

@mcp.tool
def delete_character(
    name_or_id: Annotated[str, Field(description="Character name, ID, or player name.")]
) -> str:
    """Delete a character from the current campaign. Accepts character name, ID, or player name."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    char_name = character.name
    storage.remove_character(name_or_id)
    return f"🗑️ Character '{char_name}' has been deleted from the campaign."

# NPC Management Tools
@mcp.tool
def create_npc(
    name: Annotated[str, Field(description="NPC name")],
    description: Annotated[str | None, Field(description="A brief, public description of the NPC.")] = None,
    bio: Annotated[str | None, Field(description="A detailed, private bio for the NPC, including secrets.")] = None,
    race: Annotated[str | None, Field(description="NPC race")] = None,
    occupation: Annotated[str | None, Field(description="NPC occupation")] = None,
    location: Annotated[str | None, Field(description="Current location")] = None,
    attitude: Annotated[Literal["friendly", "neutral", "hostile", "unknown"] | None, Field(description="Attitude towards party")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new NPC."""
    npc = NPC(
        name=name,
        description=description,
        bio=bio,
        race=race,
        occupation=occupation,
        location=location,
        attitude=attitude,
        notes=notes
    )

    storage.add_npc(npc)
    return f"Created NPC '{npc.name}'"

@mcp.tool
def get_npc(
    name: Annotated[str, Field(description="NPC name")]
) -> str:
    """Get NPC information."""
    npc = storage.get_npc(name)
    if not npc:
        return f"NPC '{name}' not found."

    npc_info = f"""**{npc.name}** (`{npc.id}`)
**Race:** {npc.race or 'Unknown'}
**Occupation:** {npc.occupation or 'Unknown'}
**Location:** {npc.location or 'Unknown'}
**Attitude:** {npc.attitude or 'Neutral'}

**Description:** {npc.description or 'No description available.'}
**Bio:** {npc.bio or 'No bio available.'}

**Notes:** {npc.notes or 'No additional notes.'}
"""

    return npc_info

@mcp.tool
def list_npcs(
    format: Annotated[Literal["json", "toon"], Field(description="Output format: 'json' (default) or 'toon' for compact representation")] = "json"
) -> str:
    """List all NPCs in the current campaign.

    Returns a list of all non-player characters with their basic information.
    Supports TOON format for more compact output (~30% token reduction).
    """
    npcs = storage.list_npcs_detailed()  # O(n) instead of O(2n)
    if not npcs:
        return "No NPCs in the current campaign."

    if format == "toon":
        # Convert NPC objects to dictionaries for TOON encoding
        npc_data = [npc.model_dump() for npc in npcs]
        return encode_to_toon(npc_data)

    npc_list = [
        f"• {npc.name}{f' ({npc.location})' if npc.location else ''}"
        for npc in npcs
    ]

    return "**NPCs:**\n" + "\n".join(npc_list)

# Location Management Tools
@mcp.tool
def create_location(
    name: Annotated[str, Field(description="Location name")],
    location_type: Annotated[str, Field(description="Type of location (city, town, village, dungeon, etc.)")],
    description: Annotated[str, Field(description="Location description")],
    population: Annotated[int | None, Field(description="Population (if applicable)", ge=0)] = None,
    government: Annotated[str | None, Field(description="Government type")] = None,
    notable_features: Annotated[list[str] | None, Field(description="Notable features")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new location."""
    location = Location(
        name=name,
        location_type=location_type,
        description=description,
        population=population,
        government=government,
        notable_features=notable_features or [],
        notes=notes
    )

    storage.add_location(location)
    return f"Created location '{location.name}' ({location.location_type})"

@mcp.tool
def get_location(
    name: Annotated[str, Field(description="Location name")]
) -> str:
    """Get location information."""
    location = storage.get_location(name)
    if not location:
        return f"Location '{name}' not found."

    loc_info = f"""**{location.name}** ({location.location_type})

**Description:** {location.description}

**Population:** {location.population or 'Unknown'}
**Government:** {location.government or 'Unknown'}

**Notable Features:**
{chr(10).join(['• ' + feature for feature in location.notable_features]) if location.notable_features else 'None listed'}

**Notes:** {location.notes or 'No additional notes.'}
"""

    return loc_info

@mcp.tool
def list_locations(
    format: Annotated[Literal["json", "toon"], Field(description="Output format: 'json' (default) or 'toon' for compact representation")] = "json"
) -> str:
    """List all locations in the current campaign.

    Returns a list of all locations with their basic information.
    Supports TOON format for more compact output (~30% token reduction).
    """
    locations = storage.list_locations_detailed()  # O(n) instead of O(2n)
    if not locations:
        return "No locations in the current campaign."

    if format == "toon":
        # Convert Location objects to dictionaries for TOON encoding
        loc_data = [loc.model_dump() for loc in locations]
        return encode_to_toon(loc_data)

    loc_list = [
        f"• {loc.name} ({loc.location_type})"
        for loc in locations
    ]

    return "**Locations:**\n" + "\n".join(loc_list)

# Quest Management Tools
@mcp.tool
def create_quest(
    title: Annotated[str, Field(description="Quest title")],
    description: Annotated[str, Field(description="Quest description")],
    giver: Annotated[str | None, Field(description="Quest giver (NPC name)")] = None,
    objectives: Annotated[list[str] | None, Field(description="Quest objectives")] = None,
    reward: Annotated[str | None, Field(description="Quest reward")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a new quest."""
    quest = Quest(
        title=title,
        description=description,
        giver=giver,
        objectives=objectives or [],
        reward=reward,
        notes=notes
    )

    storage.add_quest(quest)
    return f"Created quest '{quest.title}'"

@mcp.tool
def update_quest(
    title: Annotated[str, Field(description="Quest title")],
    status: Annotated[Literal["active", "completed", "failed", "on_hold"] | None, Field(description="New quest status")] = None,
    completed_objective: Annotated[str | None, Field(description="Objective to mark as completed")] = None,
) -> str:
    """Update quest status or complete objectives."""
    quest = storage.get_quest(title)
    if not quest:
        return f"Quest '{title}' not found."

    if status:
        storage.update_quest_status(title, status)

    if completed_objective:
        if completed_objective in quest.objectives and completed_objective not in quest.completed_objectives:
            quest.completed_objectives.append(completed_objective)
            storage._save_campaign()  # Direct save since we modified the object

    return f"Updated quest '{title}'"

@mcp.tool
def list_quests(
    status: Annotated[Literal["active", "completed", "failed", "on_hold"] | None, Field(description="Filter by status")] = None,
    format: Annotated[Literal["json", "toon"], Field(description="Output format: 'json' (default) or 'toon' for compact representation")] = "json"
) -> str:
    """List quests, optionally filtered by status.

    Returns a list of quests with their basic information and status.
    Supports TOON format for more compact output (~30% token reduction).
    """
    quests = storage.list_quests(status)

    if not quests:
        filter_text = f" with status '{status}'" if status else ""
        return f"No quests found{filter_text}."

    if format == "toon":
        # Get full quest objects for TOON encoding
        quest_objects = []
        for quest_title in quests:
            quest = storage.get_quest(quest_title)
            if quest:
                quest_objects.append(quest.model_dump())
        return encode_to_toon(quest_objects)

    quest_list = []
    for quest_title in quests:
        quest = storage.get_quest(quest_title)
        if quest:
            status_text = f" [{quest.status}]"
            quest_list.append(f"• {quest.title}{status_text}")

    return "**Quests:**\n" + "\n".join(quest_list)

# Game State Management Tools
@mcp.tool
def update_game_state(
    current_location: Annotated[str | None, Field(description="Current party location")] = None,
    current_session: Annotated[int | None, Field(description="Current session number", ge=1)] = None,
    current_date_in_game: Annotated[str | None, Field(description="Current in-game date")] = None,
    party_level: Annotated[int | None, Field(description="Average party level", ge=1, le=20)] = None,
    party_funds: Annotated[str | None, Field(description="Party treasure/funds")] = None,
    in_combat: Annotated[bool | None, Field(description="Whether party is in combat")] = None,
    notes: Annotated[str | None, Field(description="Current situation notes")] = None,
) -> str:
    """Update the current game state."""
    kwargs = {}
    if current_location is not None:
        kwargs["current_location"] = current_location
    if current_session is not None:
        kwargs["current_session"] = current_session
    if current_date_in_game is not None:
        kwargs["current_date_in_game"] = current_date_in_game
    if party_level is not None:
        kwargs["party_level"] = party_level
    if party_funds is not None:
        kwargs["party_funds"] = party_funds
    if in_combat is not None:
        kwargs["in_combat"] = in_combat
    if notes is not None:
        kwargs["notes"] = notes

    storage.update_game_state(**kwargs)
    return "Updated game state"

@mcp.tool
def get_game_state() -> str:
    """Get the current game state."""
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    state_info = f"""**Game State**
**Campaign:** {game_state.campaign_name}
**Session:** {game_state.current_session}
**Location:** {game_state.current_location or 'Unknown'}
**Date (In-Game):** {game_state.current_date_in_game or 'Unknown'}
**Party Level:** {game_state.party_level}
**Party Funds:** {game_state.party_funds}
**In Combat:** {'Yes' if game_state.in_combat else 'No'}

**Active Quests:** {len(game_state.active_quests)}

**Notes:** {game_state.notes or 'No current notes.'}
"""

    return state_info

# Combat Management Tools
@mcp.tool
def start_combat(
    participants: Annotated[list[dict], Field(description="Combat participants with initiative order")]
) -> str:
    """Start a combat encounter."""
    # Sort by initiative (highest first)
    initiative_order = sorted(participants, key=lambda x: x.get("initiative", 0), reverse=True)

    storage.update_game_state(
        in_combat=True,
        initiative_order=initiative_order,
        current_turn=initiative_order[0]["name"] if initiative_order else None
    )

    order_text = "\n".join([
        f"{i+1}. {p['name']} (Initiative: {p.get('initiative', 0)})"
        for i, p in enumerate(initiative_order)
    ])

    return f"**Combat Started!**\n\n**Initiative Order:**\n{order_text}\n\n**Current Turn:** {initiative_order[0]['name'] if initiative_order else 'None'}"

@mcp.tool
def end_combat() -> str:
    """End the current combat encounter."""
    storage.update_game_state(
        in_combat=False,
        initiative_order=[],
        current_turn=None
    )
    return "Combat ended."

@mcp.tool
def next_turn() -> str:
    """Advance to the next turn in combat."""
    game_state = storage.get_game_state()
    if not game_state or not game_state.in_combat:
        return "Not currently in combat."

    if not game_state.initiative_order:
        return "No initiative order set."

    # Find current turn index and advance
    current_index = 0
    if game_state.current_turn:
        for i, participant in enumerate(game_state.initiative_order):
            if participant["name"] == game_state.current_turn:
                current_index = i
                break

    next_index = (current_index + 1) % len(game_state.initiative_order)
    next_participant = game_state.initiative_order[next_index]

    storage.update_game_state(current_turn=next_participant["name"])

    return f"**Next Turn:** {next_participant['name']}"

# Session Management Tools
@mcp.tool
def add_session_note(
    session_number: Annotated[int, Field(description="Session number", ge=1)],
    summary: Annotated[str, Field(description="Session summary")],
    title: Annotated[str | None, Field(description="Session title")] = None,
    events: Annotated[list[str] | None, Field(description="Key events that occurred")] = None,
    characters_present: Annotated[list[str] | None, Field(description="Characters present in session")] = None,
    npcs_encountered: Annotated[list[str] | None, Field(description="NPCs encountered in session")] = None,
    quest_updates: Annotated[dict[str, str] | None, Field(description="Quest name to progress mapping")] = None,
    combat_encounters: Annotated[list[str] | None, Field(description="Combat encounter summaries")] = None,
    experience_gained: Annotated[int | None, Field(description="Experience points gained", ge=0)] = None,
    treasure_found: Annotated[list[str] | None, Field(description="Treasure or items found")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Add notes for a game session."""
    session_note = SessionNote(
        session_number=session_number,
        title=title,
        summary=summary,
        events=events or [],
        characters_present=characters_present or [],
        npcs_encountered=npcs_encountered or [],
        quest_updates=quest_updates or {},
        combat_encounters=combat_encounters or [],
        experience_gained=experience_gained,
        treasure_found=treasure_found or [],
        notes=notes
    )

    storage.add_session_note(session_note)
    return f"Added session note for Session {session_note.session_number}"

def _summarize_session_impl(
    transcription: str,
    session_number: int,
    detail_level: Literal["brief", "medium", "detailed"] = "medium",
    speaker_map: dict[str, str] | None = None
) -> str:
    """Implementation of summarize_session tool (separated for testing).

    Args:
        transcription: Raw text or file path containing session transcription
        session_number: Session number for this recording
        detail_level: Amount of detail in the generated summary
        speaker_map: Optional mapping of generic speaker labels to character names

    Returns:
        Formatted prompt for LLM processing
    """
    # Step 1: Detect if transcription is file path or raw text
    transcription_text = transcription
    source_type = "raw text"

    # Only check for file if input is reasonable path length (< 1000 chars)
    # and doesn't contain newlines (which wouldn't be in a valid path)
    if len(transcription) < 1000 and '\n' not in transcription:
        transcription_path = Path(transcription.strip())
        try:
            if transcription_path.exists() and transcription_path.is_file():
                transcription_text = transcription_path.read_text(encoding='utf-8')
                source_type = f"file: {transcription_path.name}"
                logger.info(f"Loaded transcription from file: {transcription_path}")
        except (OSError, Exception) as e:
            # Path validation failed or read failed - treat as raw text
            logger.debug(f"Not a valid file path: {e}. Treating input as raw text.")
            transcription_text = transcription
            source_type = "raw text"

    # Step 2: Apply speaker mapping if provided
    if speaker_map:
        logger.info(f"Applying speaker mapping: {speaker_map}")
        for speaker_label, character_name in speaker_map.items():
            # Replace speaker labels case-insensitively
            import re
            pattern = re.compile(re.escape(speaker_label), re.IGNORECASE)
            transcription_text = pattern.sub(character_name, transcription_text)

    # Step 3: Load campaign context
    logger.info("Loading campaign context for enrichment")

    characters = storage.list_characters_detailed()
    npcs = storage.list_npcs_detailed()
    locations = storage.list_locations_detailed()
    quests = storage.list_quests()

    # Create compact context using TOON format
    context = {
        "characters": [{"name": c.name, "class": c.character_class.name, "level": c.character_class.level} for c in characters],
        "npcs": [{"name": n.name, "location": n.location, "attitude": n.attitude} for n in npcs],
        "locations": [{"name": l.name, "type": l.location_type} for l in locations],
        "quests": []
    }

    # Get quest details
    for quest_title in quests:
        quest = storage.get_quest(quest_title)
        if quest:
            context["quests"].append({
                "title": quest.title,
                "status": quest.status,
                "objectives": quest.objectives
            })

    context_encoded = encode_to_toon(context)

    # Step 4: Handle large transcriptions with chunking
    CHUNK_SIZE = 40000  # ~10k tokens per chunk
    OVERLAP_SIZE = 4000  # ~1k token overlap
    LARGE_THRESHOLD = 200000  # ~50k tokens

    if len(transcription_text) > LARGE_THRESHOLD:
        logger.info(f"Large transcription detected ({len(transcription_text)} chars). Using chunking strategy.")
        chunks = _create_overlapping_chunks(transcription_text, CHUNK_SIZE, OVERLAP_SIZE)
        logger.info(f"Created {len(chunks)} overlapping chunks")

        # Return instructions for processing chunks
        prompt = _generate_chunked_summary_prompt(
            chunks=chunks,
            context=context_encoded,
            session_number=session_number,
            detail_level=detail_level,
            source_type=source_type
        )
    else:
        # Single-pass processing
        prompt = _generate_summary_prompt(
            transcription=transcription_text,
            context=context_encoded,
            session_number=session_number,
            detail_level=detail_level,
            source_type=source_type
        )

    # Return the prompt for the MCP client to process with an LLM
    return prompt


@mcp.tool
def summarize_session(
    transcription: Annotated[str, Field(description="Raw transcription text or path to transcription file")],
    session_number: Annotated[int, Field(description="Session number", ge=1)],
    detail_level: Annotated[Literal["brief", "medium", "detailed"], Field(description="Detail level for the summary")] = "medium",
    speaker_map: Annotated[dict[str, str] | None, Field(description="Speaker label to character mapping (e.g., {'Speaker 1': 'Gandalf'})")] = None
) -> str:
    """Generate structured SessionNote from a raw session transcription.

    This tool accepts either raw transcription text or a path to a transcription file,
    then generates a comprehensive structured summary including events, NPCs encountered,
    quest updates, and combat encounters. The tool leverages campaign context (characters,
    NPCs, locations, quests) to enrich the summary.

    For large transcriptions (>200k characters ≈ 50k tokens), the tool automatically
    chunks the input into overlapping segments for processing.

    Args:
        transcription: Raw text or file path containing session transcription
        session_number: Session number for this recording
        detail_level: Amount of detail in the generated summary
        speaker_map: Optional mapping of generic speaker labels to character names

    Returns:
        Prompt for LLM to generate SessionNote
    """
    return _summarize_session_impl(transcription, session_number, detail_level, speaker_map)


def _create_overlapping_chunks(text: str, chunk_size: int, overlap_size: int) -> list[str]:
    """Split text into overlapping chunks for large transcription processing.

    Args:
        text: Full transcription text
        chunk_size: Size of each chunk in characters
        overlap_size: Size of overlap between chunks

    Returns:
        List of text chunks with overlaps
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Try to find a natural break point (paragraph or sentence) only if not at the end
        if end < text_length:
            # Look for paragraph break within last 500 chars
            search_start = max(start, end - 500)
            last_para = text.rfind('\n\n', search_start, end)
            if last_para > start:
                end = last_para
            else:
                # Look for sentence break within last 200 chars
                search_start = max(start, end - 200)
                last_period = max(
                    text.rfind('. ', search_start, end),
                    text.rfind('! ', search_start, end),
                    text.rfind('? ', search_start, end)
                )
                if last_period > start:
                    end = last_period + 2

        chunks.append(text[start:end])

        # If we've reached the end, break
        if end >= text_length:
            break

        # Move start forward with overlap
        new_start = end - overlap_size

        # Ensure we're making progress (avoid infinite loop)
        if new_start <= start:
            new_start = start + 1

        start = new_start

    return chunks


def _generate_summary_prompt(transcription: str, context: str, session_number: int, detail_level: str, source_type: str) -> str:
    """Generate prompt for single-pass transcription summarization.

    Args:
        transcription: Full transcription text
        context: TOON-encoded campaign context
        session_number: Session number
        detail_level: Detail level (brief/medium/detailed)
        source_type: Description of transcription source

    Returns:
        Formatted prompt for LLM processing
    """
    detail_instructions = {
        "brief": "Create a concise summary focusing on major plot points and decisions.",
        "medium": "Create a balanced summary with key events, NPC interactions, and quest progress.",
        "detailed": "Create a comprehensive summary capturing dialogue nuances, character development, and all significant interactions."
    }

    return f"""# Session Transcription Summary Request

**Session Number:** {session_number}
**Source:** {source_type}
**Detail Level:** {detail_level}

## Campaign Context
{context}

## Instructions
{detail_instructions[detail_level]}

Generate a structured SessionNote with the following fields:
1. **title**: A catchy title for the session (max 60 chars)
2. **summary**: A narrative summary of the session
3. **events**: List of key events (bullet points)
4. **characters_present**: List of PC names who participated
5. **npcs_encountered**: List of NPC names who appeared
6. **quest_updates**: Dictionary mapping quest titles to progress descriptions
7. **combat_encounters**: List of combat summaries (if any)
8. **experience_gained**: Estimated XP earned (optional)
9. **treasure_found**: List of loot/items acquired
10. **notes**: Additional DM notes or observations

## Transcription
{transcription}

---

Please analyze the transcription above and generate a SessionNote object following the structure described. Use the campaign context to identify known characters, NPCs, locations, and quests."""


def _generate_chunked_summary_prompt(chunks: list[str], context: str, session_number: int, detail_level: str, source_type: str) -> str:
    """Generate prompt for chunked transcription summarization.

    Args:
        chunks: List of transcription chunks
        context: TOON-encoded campaign context
        session_number: Session number
        detail_level: Detail level (brief/medium/detailed)
        source_type: Description of transcription source

    Returns:
        Formatted prompt for LLM processing with chunking instructions
    """
    detail_instructions = {
        "brief": "Create a concise summary focusing on major plot points and decisions.",
        "medium": "Create a balanced summary with key events, NPC interactions, and quest progress.",
        "detailed": "Create a comprehensive summary capturing dialogue nuances, character development, and all significant interactions."
    }

    chunk_summaries = "\n\n".join([
        f"### Chunk {i+1} of {len(chunks)}\n{chunk}"
        for i, chunk in enumerate(chunks)
    ])

    return f"""# Large Session Transcription Summary Request (Chunked)

**Session Number:** {session_number}
**Source:** {source_type}
**Detail Level:** {detail_level}
**Chunks:** {len(chunks)} overlapping segments

## Campaign Context
{context}

## Instructions
This transcription has been split into {len(chunks)} overlapping chunks for processing.

**Phase 1: Extract events from each chunk**
- Process each chunk independently
- Extract key events with normalized titles (e.g., "Combat with goblins" not "Combat with goblins in chunk 2")
- Note: Events may appear in multiple chunks due to overlap

**Phase 2: Merge and deduplicate**
- Combine events from all chunks
- Remove duplicates by comparing normalized event titles
- Maintain chronological order

**Phase 3: Generate final SessionNote**
{detail_instructions[detail_level]}

Generate a structured SessionNote with the following fields:
1. **title**: A catchy title for the session (max 60 chars)
2. **summary**: A narrative summary of the entire session
3. **events**: Deduplicated list of key events from all chunks
4. **characters_present**: List of PC names who participated
5. **npcs_encountered**: List of NPC names who appeared
6. **quest_updates**: Dictionary mapping quest titles to progress descriptions
7. **combat_encounters**: List of combat summaries
8. **experience_gained**: Estimated XP earned (optional)
9. **treasure_found**: List of loot/items acquired
10. **notes**: Additional DM notes or observations

## Transcription Chunks
{chunk_summaries}

---

Please analyze all chunks above and generate a single cohesive SessionNote object following the structure described. Use the campaign context to identify known characters, NPCs, locations, and quests. Remember to deduplicate events that appear in multiple chunks."""

@mcp.tool
def get_sessions() -> str:
    """Get all session notes."""
    sessions = storage.get_sessions()
    if not sessions:
        return "No session notes recorded."

    session_list = []
    for session in sorted(sessions, key=lambda s: s.session_number):
        title = session.title or "No title"
        date = session.date.strftime("%Y-%m-%d")
        session_list.append(f"**Session {session.session_number}** ({date}): {title}")
        session_list.append(f"  {session.summary[:100]}{'...' if len(session.summary) > 100 else ''}")
        session_list.append("")

    return "**Session Notes:**\n\n" + "\n".join(session_list)

# Adventure Log Tools
@mcp.tool
def add_event(
    event_type: Annotated[Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"], Field(description="Type of event")],
    title: Annotated[str, Field(description="Event title")],
    description: Annotated[str, Field(description="Event description")],
    session_number: Annotated[int | None, Field(description="Session number", ge=1)] = None,
    characters_involved: Annotated[list[str] | None, Field(description="Characters involved in the event")] = None,
    location: Annotated[str | None, Field(description="Location where event occurred")] = None,
    importance: Annotated[int, Field(description="Event importance (1-5)", ge=1, le=5)] = 3,
    tags: Annotated[list[str] | None, Field(description="Tags for categorizing the event")] = None,
) -> str:
    """Add an event to the adventure log."""
    event = AdventureEvent(
        event_type=EventType(event_type),
        title=title,
        description=description,
        session_number=session_number,
        characters_involved=characters_involved or [],
        location=location,
        importance=importance,
        tags=tags or []
    )

    storage.add_event(event)
    return f"Added {event_type.lower} event: '{event.title}'"

@mcp.tool
def get_events(
    limit: Annotated[int | None, Field(description="Maximum number of events to return", ge=1)] = None,
    event_type: Annotated[Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"] | None, Field(description="Filter by event type")] = None,
    search: Annotated[str | None, Field(description="Search events by title/description")] = None,
) -> str:
    """Get events from the adventure log."""
    if search:
        events = storage.search_events(search)
    else:
        events = storage.get_events(limit=limit, event_type=event_type)

    if not events:
        return "No events found."

    event_list = []
    for event in events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M")
        session_text = f" (Session {event.session_number})" if event.session_number else ""
        importance_stars = "★" * event.importance

        event_list.append(f"**{event.title}** [{event.event_type}] {importance_stars}")
        event_list.append(f"  {timestamp}{session_text}")
        event_list.append(f"  {event.description[:150]}{'...' if len(event.description) > 150 else ''}")
        if event.location:
            event_list.append(f"  📍 {event.location}")
        event_list.append("")

    return "**Adventure Log:**\n\n" + "\n".join(event_list)

# Utility Tools
@mcp.tool
def roll_dice(
    dice_notation: Annotated[str, Field(description="Dice notation (e.g., '1d20', '3d6+2')")],
    advantage: Annotated[bool, Field(description="Roll with advantage")] = False,
    disadvantage: Annotated[bool, Field(description="Roll with disadvantage")] = False,
) -> str:
    """Roll dice with D&D notation."""
    dice_notation = dice_notation.lower().strip()

    # Parse dice notation (e.g., "1d20", "3d6+2", "2d8-1")
    pattern = r'(\d+)d(\d+)([+-]\d+)?'
    match = re.match(pattern, dice_notation)

    if not match:
        return f"Invalid dice notation: {dice_notation}"

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    # Roll dice
    if advantage or disadvantage:
        if num_dice != 1 or die_size != 20:
            return "Advantage/disadvantage only applies to single d20 rolls"

        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)

        if advantage:
            result = max(roll1, roll2)
            roll_text = f"Advantage: {roll1}, {roll2} (taking {result})"
        else:
            result = min(roll1, roll2)
            roll_text = f"Disadvantage: {roll1}, {roll2} (taking {result})"

        total = result + modifier
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** {roll_text}{modifier_text} = **{total}**"
    else:
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        roll_sum = sum(rolls)
        total = roll_sum + modifier

        rolls_text = ", ".join(map(str, rolls)) if num_dice > 1 else str(rolls[0])
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** [{rolls_text}]{modifier_text} = **{total}**"

@mcp.tool
def calculate_experience(
    party_size: Annotated[int, Field(description="Number of party members", ge=1)],
    party_level: Annotated[int, Field(description="Average party level", ge=1, le=20)],
    encounter_xp: Annotated[int, Field(description="Total encounter XP value", ge=0)],
) -> str:
    """Calculate experience points for an encounter."""
    # D&D 5e encounter multipliers based on party size
    if party_size < 3:
        multiplier = 1.5
    elif party_size > 5:
        multiplier = 0.5
    else:
        multiplier = 1.0

    adjusted_xp = int(encounter_xp * multiplier)
    xp_per_player = adjusted_xp // party_size

    return f"""**Experience Calculation:**
Base Encounter XP: {encounter_xp}
Party Size Multiplier: {multiplier}x
Adjusted XP: {adjusted_xp}
**XP per Player: {xp_per_player}**"""

logger.debug("✅ All tools successfully registered. Gamemaster-MCP server running! 🎲")

def main() -> None:
    """Main entry point for the D&D MCP Server."""
    mcp.run()

if __name__ == "__main__":
    main()
