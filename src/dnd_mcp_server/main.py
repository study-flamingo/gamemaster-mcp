"""
D&D MCP Server - Main server implementation with tools for campaign management.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import AnyUrl

from .storage import DnDStorage
from .models import (
    Campaign, Character, NPC, Location, Quest, CombatEncounter,
    SessionNote, GameState, AdventureEvent, EventType, AbilityScore,
    CharacterClass, Race, Item, Spell
)

# Initialize storage
storage = DnDStorage()

# Create the MCP server
app = Server("dnd-mcp-server")


@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available D&D tools."""
    return [
        # Campaign Management
        Tool(
            name="create_campaign",
            description="Create a new D&D campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name"},
                    "description": {"type": "string", "description": "Campaign description"},
                    "dm_name": {"type": "string", "description": "Dungeon Master name"},
                    "setting": {"type": "string", "description": "Campaign setting"},
                },
                "required": ["name", "description"]
            }
        ),
        Tool(
            name="get_campaign_info",
            description="Get information about the current campaign",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="list_campaigns",
            description="List all available campaigns",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="load_campaign",
            description="Load a specific campaign",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Campaign name to load"}
                },
                "required": ["name"]
            }
        ),
        
        # Character Management
        Tool(
            name="create_character",
            description="Create a new player character",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Character name"},
                    "player_name": {"type": "string", "description": "Player name"},
                    "character_class": {"type": "string", "description": "Character class"},
                    "class_level": {"type": "integer", "description": "Class level", "minimum": 1, "maximum": 20},
                    "race": {"type": "string", "description": "Character race"},
                    "background": {"type": "string", "description": "Character background"},
                    "alignment": {"type": "string", "description": "Character alignment"},
                    "abilities": {
                        "type": "object",
                        "description": "Ability scores",
                        "properties": {
                            "strength": {"type": "integer", "minimum": 1, "maximum": 30},
                            "dexterity": {"type": "integer", "minimum": 1, "maximum": 30},
                            "constitution": {"type": "integer", "minimum": 1, "maximum": 30},
                            "intelligence": {"type": "integer", "minimum": 1, "maximum": 30},
                            "wisdom": {"type": "integer", "minimum": 1, "maximum": 30},
                            "charisma": {"type": "integer", "minimum": 1, "maximum": 30},
                        }
                    }
                },
                "required": ["name", "character_class", "class_level", "race"]
            }
        ),
        Tool(
            name="get_character",
            description="Get character information",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Character name"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="update_character_hp",
            description="Update character hit points",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Character name"},
                    "current_hp": {"type": "integer", "description": "Current hit points"},
                    "max_hp": {"type": "integer", "description": "Maximum hit points"},
                    "temp_hp": {"type": "integer", "description": "Temporary hit points", "default": 0}
                },
                "required": ["name", "current_hp"]
            }
        ),
        Tool(
            name="add_item_to_character",
            description="Add an item to a character's inventory",
            inputSchema={
                "type": "object",
                "properties": {
                    "character_name": {"type": "string", "description": "Character name"},
                    "item_name": {"type": "string", "description": "Item name"},
                    "description": {"type": "string", "description": "Item description"},
                    "quantity": {"type": "integer", "description": "Quantity", "default": 1},
                    "item_type": {"type": "string", "description": "Item type (weapon, armor, consumable, misc)"},
                    "weight": {"type": "number", "description": "Item weight"},
                    "value": {"type": "string", "description": "Item value (e.g., '50 gp')"}
                },
                "required": ["character_name", "item_name"]
            }
        ),
        Tool(
            name="list_characters",
            description="List all characters in the current campaign",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # NPC Management
        Tool(
            name="create_npc",
            description="Create a new NPC",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "NPC name"},
                    "description": {"type": "string", "description": "NPC description"},
                    "race": {"type": "string", "description": "NPC race"},
                    "occupation": {"type": "string", "description": "NPC occupation"},
                    "location": {"type": "string", "description": "Current location"},
                    "attitude": {"type": "string", "description": "Attitude towards party"},
                    "notes": {"type": "string", "description": "Additional notes"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="get_npc",
            description="Get NPC information",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "NPC name"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_npcs",
            description="List all NPCs in the current campaign",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Location Management
        Tool(
            name="create_location",
            description="Create a new location",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Location name"},
                    "location_type": {"type": "string", "description": "Type of location"},
                    "description": {"type": "string", "description": "Location description"},
                    "population": {"type": "integer", "description": "Population (if applicable)"},
                    "government": {"type": "string", "description": "Government type"},
                    "notable_features": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Notable features"
                    },
                    "notes": {"type": "string", "description": "Additional notes"}
                },
                "required": ["name", "location_type", "description"]
            }
        ),
        Tool(
            name="get_location",
            description="Get location information",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Location name"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="list_locations",
            description="List all locations in the current campaign",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Quest Management
        Tool(
            name="create_quest",
            description="Create a new quest",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Quest title"},
                    "description": {"type": "string", "description": "Quest description"},
                    "giver": {"type": "string", "description": "Quest giver (NPC name)"},
                    "objectives": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Quest objectives"
                    },
                    "reward": {"type": "string", "description": "Quest reward"},
                    "notes": {"type": "string", "description": "Additional notes"}
                },
                "required": ["title", "description"]
            }
        ),
        Tool(
            name="update_quest",
            description="Update quest status or complete objectives",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Quest title"},
                    "status": {"type": "string", "description": "New status (active, completed, failed, on_hold)"},
                    "completed_objective": {"type": "string", "description": "Objective to mark as completed"}
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="list_quests",
            description="List quests, optionally filtered by status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status"}
                }
            }
        ),
        
        # Game State Management
        Tool(
            name="update_game_state",
            description="Update the current game state",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_location": {"type": "string", "description": "Current party location"},
                    "current_session": {"type": "integer", "description": "Current session number"},
                    "current_date_in_game": {"type": "string", "description": "Current in-game date"},
                    "party_level": {"type": "integer", "description": "Average party level"},
                    "party_funds": {"type": "string", "description": "Party treasure/funds"},
                    "in_combat": {"type": "boolean", "description": "Whether party is in combat"},
                    "notes": {"type": "string", "description": "Current situation notes"}
                }
            }
        ),
        Tool(
            name="get_game_state",
            description="Get the current game state",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Combat Management
        Tool(
            name="start_combat",
            description="Start a combat encounter",
            inputSchema={
                "type": "object",
                "properties": {
                    "participants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "initiative": {"type": "integer"},
                                "is_player": {"type": "boolean", "default": False}
                            },
                            "required": ["name", "initiative"]
                        },
                        "description": "Combat participants with initiative order"
                    }
                },
                "required": ["participants"]
            }
        ),
        Tool(
            name="end_combat",
            description="End the current combat encounter",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="next_turn",
            description="Advance to the next turn in combat",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Session Management
        Tool(
            name="add_session_note",
            description="Add notes for a game session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_number": {"type": "integer", "description": "Session number"},
                    "title": {"type": "string", "description": "Session title"},
                    "summary": {"type": "string", "description": "Session summary"},
                    "events": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key events that occurred"
                    },
                    "characters_present": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Characters present in session"
                    },
                    "experience_gained": {"type": "integer", "description": "Experience points gained"},
                    "treasure_found": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Treasure or items found"
                    },
                    "notes": {"type": "string", "description": "Additional notes"}
                },
                "required": ["session_number", "summary"]
            }
        ),
        Tool(
            name="get_sessions",
            description="Get all session notes",
            inputSchema={"type": "object", "properties": {}}
        ),
        
        # Adventure Log
        Tool(
            name="add_event",
            description="Add an event to the adventure log",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string", 
                        "enum": ["combat", "roleplay", "exploration", "quest", "character", "world", "session"],
                        "description": "Type of event"
                    },
                    "title": {"type": "string", "description": "Event title"},
                    "description": {"type": "string", "description": "Event description"},
                    "session_number": {"type": "integer", "description": "Session number"},
                    "characters_involved": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Characters involved in the event"
                    },
                    "location": {"type": "string", "description": "Location where event occurred"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Event importance (1-5)"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing the event"
                    }
                },
                "required": ["event_type", "title", "description"]
            }
        ),
        Tool(
            name="get_events",
            description="Get events from the adventure log",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of events to return"},
                    "event_type": {"type": "string", "description": "Filter by event type"},
                    "search": {"type": "string", "description": "Search events by title/description"}
                }
            }
        ),
        
        # Utility Tools
        Tool(
            name="roll_dice",
            description="Roll dice with D&D notation (e.g., '1d20', '3d6+2')",
            inputSchema={
                "type": "object",
                "properties": {
                    "dice_notation": {"type": "string", "description": "Dice notation (e.g., '1d20', '3d6+2')"},
                    "advantage": {"type": "boolean", "description": "Roll with advantage", "default": False},
                    "disadvantage": {"type": "boolean", "description": "Roll with disadvantage", "default": False}
                },
                "required": ["dice_notation"]
            }
        ),
        Tool(
            name="calculate_experience",
            description="Calculate experience points for an encounter",
            inputSchema={
                "type": "object",
                "properties": {
                    "party_size": {"type": "integer", "description": "Number of party members"},
                    "party_level": {"type": "integer", "description": "Average party level"},
                    "encounter_xp": {"type": "integer", "description": "Total encounter XP value"}
                },
                "required": ["party_size", "party_level", "encounter_xp"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    
    try:
        if name == "create_campaign":
            campaign = storage.create_campaign(
                name=arguments["name"],
                description=arguments["description"],
                dm_name=arguments.get("dm_name"),
                setting=arguments.get("setting")
            )
            return [TextContent(
                type="text",
                text=f"Created campaign '{campaign.name}'. Campaign is now active."
            )]
        
        elif name == "get_campaign_info":
            campaign = storage.get_current_campaign()
            if not campaign:
                return [TextContent(type="text", text="No active campaign.")]
            
            info = {
                "name": campaign.name,
                "description": campaign.description,
                "dm_name": campaign.dm_name,
                "setting": campaign.setting,
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
            
            return [TextContent(
                type="text",
                text=f"**Campaign: {campaign.name}**\\n\\n" + 
                     "\\n".join([f"**{k.replace('_', ' ').title()}:** {v}" for k, v in info.items()])
            )]
        
        elif name == "list_campaigns":
            campaigns = storage.list_campaigns()
            if not campaigns:
                return [TextContent(type="text", text="No campaigns found.")]
            
            current = storage.get_current_campaign()
            current_name = current.name if current else None
            
            campaign_list = []
            for campaign in campaigns:
                marker = " (current)" if campaign == current_name else ""
                campaign_list.append(f"• {campaign}{marker}")
            
            return [TextContent(
                type="text",
                text="**Available Campaigns:**\\n" + "\\n".join(campaign_list)
            )]
        
        elif name == "load_campaign":
            campaign = storage.load_campaign(arguments["name"])
            return [TextContent(
                type="text",
                text=f"Loaded campaign '{campaign.name}'. Campaign is now active."
            )]
        
        elif name == "create_character":
            # Build ability scores
            abilities = {}
            if "abilities" in arguments:
                for ability, score in arguments["abilities"].items():
                    abilities[ability] = AbilityScore(score=score)
            else:
                # Default scores
                for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
                    abilities[ability] = AbilityScore(score=10)
            
            character = Character(
                name=arguments["name"],
                player_name=arguments.get("player_name"),
                character_class=CharacterClass(
                    name=arguments["character_class"],
                    level=arguments["class_level"]
                ),
                race=Race(name=arguments["race"]),
                background=arguments.get("background"),
                alignment=arguments.get("alignment"),
                abilities=abilities
            )
            
            storage.add_character(character)
            return [TextContent(
                type="text",
                text=f"Created character '{character.name}' (Level {character.character_class.level} {character.race.name} {character.character_class.name})"
            )]
        
        elif name == "get_character":
            character = storage.get_character(arguments["name"])
            if not character:
                return [TextContent(type="text", text=f"Character '{arguments['name']}' not found.")]
            
            char_info = f"""**{character.name}**
Level {character.character_class.level} {character.race.name} {character.character_class.name}
**Player:** {character.player_name or 'N/A'}
**Background:** {character.background or 'N/A'}
**Alignment:** {character.alignment or 'N/A'}

**Ability Scores:**
• STR: {character.abilities['strength'].score} ({character.abilities['strength'].modifier:+d})
• DEX: {character.abilities['dexterity'].score} ({character.abilities['dexterity'].modifier:+d})
• CON: {character.abilities['constitution'].score} ({character.abilities['constitution'].modifier:+d})
• INT: {character.abilities['intelligence'].score} ({character.abilities['intelligence'].modifier:+d})
• WIS: {character.abilities['wisdom'].score} ({character.abilities['wisdom'].modifier:+d})
• CHA: {character.abilities['charisma'].score} ({character.abilities['charisma'].modifier:+d})

**Combat Stats:**
• AC: {character.armor_class}
• HP: {character.hit_points_current}/{character.hit_points_max}
• Temp HP: {character.temporary_hit_points}

**Inventory:** {len(character.inventory)} items
"""
            
            return [TextContent(type="text", text=char_info)]
        
        elif name == "update_character_hp":
            storage.update_character(
                arguments["name"],
                hit_points_current=arguments["current_hp"],
                hit_points_max=arguments.get("max_hp", arguments["current_hp"]),
                temporary_hit_points=arguments.get("temp_hp", 0)
            )
            return [TextContent(
                type="text",
                text=f"Updated {arguments['name']}'s hit points to {arguments['current_hp']}"
            )]
        
        elif name == "add_item_to_character":
            character = storage.get_character(arguments["character_name"])
            if not character:
                return [TextContent(type="text", text=f"Character '{arguments['character_name']}' not found.")]
            
            item = Item(
                name=arguments["item_name"],
                description=arguments.get("description"),
                quantity=arguments.get("quantity", 1),
                item_type=arguments.get("item_type", "misc"),
                weight=arguments.get("weight"),
                value=arguments.get("value")
            )
            
            character.inventory.append(item)
            storage.update_character(arguments["character_name"], inventory=character.inventory)
            
            return [TextContent(
                type="text",
                text=f"Added {item.quantity}x {item.name} to {character.name}'s inventory"
            )]
        
        elif name == "list_characters":
            characters = storage.list_characters()
            if not characters:
                return [TextContent(type="text", text="No characters in the current campaign.")]
            
            char_list = []
            for char_name in characters:
                char = storage.get_character(char_name)
                if char:
                    char_list.append(f"• {char.name} (Level {char.character_class.level} {char.race.name} {char.character_class.name})")
            
            return [TextContent(
                type="text",
                text="**Characters:**\\n" + "\\n".join(char_list)
            )]
        
        elif name == "create_npc":
            npc = NPC(
                name=arguments["name"],
                description=arguments.get("description"),
                race=arguments.get("race"),
                occupation=arguments.get("occupation"),
                location=arguments.get("location"),
                attitude=arguments.get("attitude"),
                notes=arguments.get("notes", "")
            )
            
            storage.add_npc(npc)
            return [TextContent(
                type="text",
                text=f"Created NPC '{npc.name}'"
            )]
        
        elif name == "get_npc":
            npc = storage.get_npc(arguments["name"])
            if not npc:
                return [TextContent(type="text", text=f"NPC '{arguments['name']}' not found.")]
            
            npc_info = f"""**{npc.name}**
**Race:** {npc.race or 'Unknown'}
**Occupation:** {npc.occupation or 'Unknown'}
**Location:** {npc.location or 'Unknown'}
**Attitude:** {npc.attitude or 'Neutral'}

**Description:** {npc.description or 'No description available.'}

**Notes:** {npc.notes or 'No additional notes.'}
"""
            
            return [TextContent(type="text", text=npc_info)]
        
        elif name == "list_npcs":
            npcs = storage.list_npcs()
            if not npcs:
                return [TextContent(type="text", text="No NPCs in the current campaign.")]
            
            npc_list = []
            for npc_name in npcs:
                npc = storage.get_npc(npc_name)
                if npc:
                    location = f" ({npc.location})" if npc.location else ""
                    npc_list.append(f"• {npc.name}{location}")
            
            return [TextContent(
                type="text",
                text="**NPCs:**\\n" + "\\n".join(npc_list)
            )]
        
        elif name == "create_location":
            location = Location(
                name=arguments["name"],
                location_type=arguments["location_type"],
                description=arguments["description"],
                population=arguments.get("population"),
                government=arguments.get("government"),
                notable_features=arguments.get("notable_features", []),
                notes=arguments.get("notes", "")
            )
            
            storage.add_location(location)
            return [TextContent(
                type="text",
                text=f"Created location '{location.name}' ({location.location_type})"
            )]
        
        elif name == "get_location":
            location = storage.get_location(arguments["name"])
            if not location:
                return [TextContent(type="text", text=f"Location '{arguments['name']}' not found.")]
            
            loc_info = f"""**{location.name}** ({location.location_type})

**Description:** {location.description}

**Population:** {location.population or 'Unknown'}
**Government:** {location.government or 'Unknown'}

**Notable Features:**
{chr(10).join(['• ' + feature for feature in location.notable_features]) if location.notable_features else 'None listed'}

**Notes:** {location.notes or 'No additional notes.'}
"""
            
            return [TextContent(type="text", text=loc_info)]
        
        elif name == "list_locations":
            locations = storage.list_locations()
            if not locations:
                return [TextContent(type="text", text="No locations in the current campaign.")]
            
            loc_list = []
            for loc_name in locations:
                loc = storage.get_location(loc_name)
                if loc:
                    loc_list.append(f"• {loc.name} ({loc.location_type})")
            
            return [TextContent(
                type="text",
                text="**Locations:**\\n" + "\\n".join(loc_list)
            )]
        
        elif name == "create_quest":
            quest = Quest(
                title=arguments["title"],
                description=arguments["description"],
                giver=arguments.get("giver"),
                objectives=arguments.get("objectives", []),
                reward=arguments.get("reward"),
                notes=arguments.get("notes", "")
            )
            
            storage.add_quest(quest)
            return [TextContent(
                type="text",
                text=f"Created quest '{quest.title}'"
            )]
        
        elif name == "update_quest":
            quest = storage.get_quest(arguments["title"])
            if not quest:
                return [TextContent(type="text", text=f"Quest '{arguments['title']}' not found.")]
            
            if "status" in arguments:
                storage.update_quest_status(arguments["title"], arguments["status"])
                
            if "completed_objective" in arguments:
                objective = arguments["completed_objective"]
                if objective in quest.objectives and objective not in quest.completed_objectives:
                    quest.completed_objectives.append(objective)
                    storage._save_campaign()  # Direct save since we modified the object
            
            return [TextContent(
                type="text",
                text=f"Updated quest '{arguments['title']}'"
            )]
        
        elif name == "list_quests":
            status_filter = arguments.get("status")
            quests = storage.list_quests(status_filter)
            
            if not quests:
                filter_text = f" with status '{status_filter}'" if status_filter else ""
                return [TextContent(type="text", text=f"No quests found{filter_text}.")]
            
            quest_list = []
            for quest_title in quests:
                quest = storage.get_quest(quest_title)
                if quest:
                    status_text = f" [{quest.status}]"
                    quest_list.append(f"• {quest.title}{status_text}")
            
            return [TextContent(
                type="text",
                text="**Quests:**\\n" + "\\n".join(quest_list)
            )]
        
        elif name == "update_game_state":
            storage.update_game_state(**arguments)
            return [TextContent(
                type="text",
                text="Updated game state"
            )]
        
        elif name == "get_game_state":
            game_state = storage.get_game_state()
            if not game_state:
                return [TextContent(type="text", text="No game state available.")]
            
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
            
            return [TextContent(type="text", text=state_info)]
        
        elif name == "start_combat":
            participants = arguments["participants"]
            # Sort by initiative (highest first)
            initiative_order = sorted(participants, key=lambda x: x["initiative"], reverse=True)
            
            storage.update_game_state(
                in_combat=True,
                initiative_order=initiative_order,
                current_turn=initiative_order[0]["name"] if initiative_order else None
            )
            
            order_text = "\\n".join([
                f"{i+1}. {p['name']} (Initiative: {p['initiative']})"
                for i, p in enumerate(initiative_order)
            ])
            
            return [TextContent(
                type="text",
                text=f"**Combat Started!**\\n\\n**Initiative Order:**\\n{order_text}\\n\\n**Current Turn:** {initiative_order[0]['name'] if initiative_order else 'None'}"
            )]
        
        elif name == "end_combat":
            storage.update_game_state(
                in_combat=False,
                initiative_order=[],
                current_turn=None
            )
            return [TextContent(type="text", text="Combat ended.")]
        
        elif name == "next_turn":
            game_state = storage.get_game_state()
            if not game_state or not game_state.in_combat:
                return [TextContent(type="text", text="Not currently in combat.")]
            
            if not game_state.initiative_order:
                return [TextContent(type="text", text="No initiative order set.")]
            
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
            
            return [TextContent(
                type="text",
                text=f"**Next Turn:** {next_participant['name']}"
            )]
        
        elif name == "add_session_note":
            session_note = SessionNote(
                session_number=arguments["session_number"],
                title=arguments.get("title"),
                summary=arguments["summary"],
                events=arguments.get("events", []),
                characters_present=arguments.get("characters_present", []),
                experience_gained=arguments.get("experience_gained"),
                treasure_found=arguments.get("treasure_found", []),
                notes=arguments.get("notes", "")
            )
            
            storage.add_session_note(session_note)
            return [TextContent(
                type="text",
                text=f"Added session note for Session {session_note.session_number}"
            )]
        
        elif name == "get_sessions":
            sessions = storage.get_sessions()
            if not sessions:
                return [TextContent(type="text", text="No session notes recorded.")]
            
            session_list = []
            for session in sorted(sessions, key=lambda s: s.session_number):
                title = session.title or "No title"
                date = session.date.strftime("%Y-%m-%d")
                session_list.append(f"**Session {session.session_number}** ({date}): {title}")
                session_list.append(f"  {session.summary[:100]}{'...' if len(session.summary) > 100 else ''}")
                session_list.append("")
            
            return [TextContent(
                type="text",
                text="**Session Notes:**\\n\\n" + "\\n".join(session_list)
            )]
        
        elif name == "add_event":
            event = AdventureEvent(
                event_type=EventType(arguments["event_type"]),
                title=arguments["title"],
                description=arguments["description"],
                session_number=arguments.get("session_number"),
                characters_involved=arguments.get("characters_involved", []),
                location=arguments.get("location"),
                importance=arguments.get("importance", 3),
                tags=arguments.get("tags", [])
            )
            
            storage.add_event(event)
            return [TextContent(
                type="text",
                text=f"Added {event.event_type} event: '{event.title}'"
            )]
        
        elif name == "get_events":
            limit = arguments.get("limit")
            event_type = arguments.get("event_type")
            search = arguments.get("search")
            
            if search:
                events = storage.search_events(search)
            else:
                events = storage.get_events(limit=limit, event_type=event_type)
            
            if not events:
                return [TextContent(type="text", text="No events found.")]
            
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
            
            return [TextContent(
                type="text",
                text="**Adventure Log:**\\n\\n" + "\\n".join(event_list)
            )]
        
        elif name == "roll_dice":
            import random
            import re
            
            dice_notation = arguments["dice_notation"].lower().strip()
            advantage = arguments.get("advantage", False)
            disadvantage = arguments.get("disadvantage", False)
            
            # Parse dice notation (e.g., "1d20", "3d6+2", "2d8-1")
            pattern = r'(\d+)d(\d+)([+-]\d+)?'
            match = re.match(pattern, dice_notation)
            
            if not match:
                return [TextContent(type="text", text=f"Invalid dice notation: {dice_notation}")]
            
            num_dice = int(match.group(1))
            die_size = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0
            
            # Roll dice
            if advantage or disadvantage:
                if num_dice != 1 or die_size != 20:
                    return [TextContent(type="text", text="Advantage/disadvantage only applies to single d20 rolls")]
                
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
                
                return [TextContent(
                    type="text",
                    text=f"🎲 **{dice_notation}** {roll_text}{modifier_text} = **{total}**"
                )]
            else:
                rolls = [random.randint(1, die_size) for _ in range(num_dice)]
                roll_sum = sum(rolls)
                total = roll_sum + modifier
                
                rolls_text = ", ".join(map(str, rolls)) if num_dice > 1 else str(rolls[0])
                modifier_text = f" {modifier:+d}" if modifier != 0 else ""
                
                return [TextContent(
                    type="text",
                    text=f"🎲 **{dice_notation}** [{rolls_text}]{modifier_text} = **{total}**"
                )]
        
        elif name == "calculate_experience":
            party_size = arguments["party_size"]
            party_level = arguments["party_level"]
            encounter_xp = arguments["encounter_xp"]
            
            # D&D 5e encounter multipliers based on party size
            if party_size < 3:
                multiplier = 1.5
            elif party_size > 5:
                multiplier = 0.5
            else:
                multiplier = 1.0
            
            adjusted_xp = int(encounter_xp * multiplier)
            xp_per_player = adjusted_xp // party_size
            
            return [TextContent(
                type="text",
                text=f"**Experience Calculation:**\\n" +
                     f"Base Encounter XP: {encounter_xp}\\n" +
                     f"Party Size Multiplier: {multiplier}x\\n" +
                     f"Adjusted XP: {adjusted_xp}\\n" +
                     f"**XP per Player: {xp_per_player}**"
            )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]


async def main():
    """Main entry point for the D&D MCP Server."""
    # Run the server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dnd-mcp-server",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
