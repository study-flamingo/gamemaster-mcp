# D&D MCP Server

A comprehensive Model Context Protocol (MCP) server for managing Dungeons & Dragons campaigns. This server provides tools for managing characters, NPCs, locations, quests, combat encounters, session notes, and more.

## Features

### Campaign Management
- Create and manage multiple campaigns
- Switch between campaigns
- Track campaign metadata (name, description, DM, setting)

### Character Management
- Complete character sheets with D&D 5e stats
- Ability scores with automatic modifier calculation
- Hit points, armor class, and combat stats
- Inventory and equipment management
- Spellcasting support

### NPC Management
- Create and track non-player characters
- Manage relationships and locations
- Store descriptions and notes

### Location/World Building
- Create detailed locations (cities, dungeons, etc.)
- Track populations, governments, and notable features
- Connect locations and manage geography

### Quest Management
- Create quests with objectives and rewards
- Track quest status and completion
- Link quests to NPCs and locations

### Combat Management
- Initiative tracking
- Turn-based combat flow
- Combat encounter planning

### Session Management
- Session notes and summaries
- Experience and treasure tracking
- Character attendance

### Adventure Log
- Comprehensive event logging
- Categorized by event type (combat, roleplay, exploration, etc.)
- Searchable and filterable
- Importance ratings

### Game State Tracking
- Current location and session
- Party level and funds
- Combat status
- In-game date tracking

### Utility Tools
- Dice rolling with advantage/disadvantage
- Experience point calculations
- D&D 5e mechanics support

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Usage

### Running the Server

```bash
python -m dnd_mcp_server
```

Or using the installed script:

```bash
dnd-mcp-server
```

### MCP Client Configuration

Add this server to your MCP client configuration. For Claude Desktop, add to your config file:

```json
{
  "mcpServers": {
    "dnd-mcp-server": {
      "command": "python",
      "args": ["-m", "dnd_mcp_server"],
      "cwd": "/path/to/dnd-mcp"
    }
  }
}
```

## Available Tools

### Campaign Tools
- `create_campaign`: Create a new campaign
- `get_campaign_info`: Get current campaign information
- `list_campaigns`: List all available campaigns
- `load_campaign`: Switch to a different campaign

### Character Tools
- `create_character`: Create a new player character
- `get_character`: Get character sheet details
- `update_character_hp`: Update character hit points
- `add_item_to_character`: Add items to inventory
- `list_characters`: List all characters

### NPC Tools
- `create_npc`: Create a new NPC
- `get_npc`: Get NPC details
- `list_npcs`: List all NPCs

### Location Tools
- `create_location`: Create a new location
- `get_location`: Get location details
- `list_locations`: List all locations

### Quest Tools
- `create_quest`: Create a new quest
- `update_quest`: Update quest status or objectives
- `list_quests`: List quests (optionally filtered by status)

### Game State Tools
- `update_game_state`: Update current game state
- `get_game_state`: Get current game state

### Combat Tools
- `start_combat`: Initialize combat with initiative order
- `end_combat`: End combat encounter
- `next_turn`: Advance to next participant's turn

### Session Tools
- `add_session_note`: Add session notes and summary
- `get_sessions`: Get all session notes

### Adventure Log Tools
- `add_event`: Add event to adventure log
- `get_events`: Get events (with filtering and search)

### Utility Tools
- `roll_dice`: Roll dice with D&D notation (e.g., "1d20", "3d6+2")
- `calculate_experience`: Calculate XP distribution for encounters

## Data Storage

The server stores all data in JSON files in a `dnd_data` directory:

```
dnd_data/
├── campaigns/
│   ├── My_Campaign.json
│   └── Another_Campaign.json
└── events/
    └── adventure_log.json
```

## Example Usage

### Creating a Campaign

```
Use the create_campaign tool:
- name: "Curse of Strahd"
- description: "A gothic horror adventure in Barovia"
- dm_name: "John Smith"
- setting: "Ravenloft"
```

### Creating a Character

```
Use the create_character tool:
- name: "Gandalf the Grey"
- character_class: "Wizard"
- class_level: 5
- race: "Human"
- abilities: {
    "strength": 10,
    "dexterity": 14,
    "constitution": 12,
    "intelligence": 18,
    "wisdom": 16,
    "charisma": 13
  }
```

### Rolling Dice

```
Use the roll_dice tool:
- dice_notation: "1d20+5"
- advantage: true (optional)
```

### Adding Events

```
Use the add_event tool:
- event_type: "combat"
- title: "Battle with the Dragon"
- description: "The party fought a young red dragon in its lair"
- importance: 5
- characters_involved: ["Gandalf", "Legolas", "Gimli"]
- location: "Dragon's Lair"
```

## Development

To extend the server:

1. Add new models in `models.py`
2. Extend storage methods in `storage.py`
3. Add new tools in `main.py`
4. Update the tool list and handlers

## License

MIT License
