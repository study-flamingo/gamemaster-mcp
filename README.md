# Gamemaster MCP 🐉

A comprehensive (Model Context Protocol (MCP))[https://www.github.com/modelcontextprotocol] server for managing AI-assisted Dungeons & Dragons campaigns, built with **FastMCP 2.9.0+**

## ✨ Features

### 🚩 Campaign Management

- Create and manage multiple campaigns
- Switch between campaigns seamlessly
- Track campaign metadata (name, description, DM, setting)

### 📑 Character Management

- Complete character sheets with D&D 5e stats
- Ability scores with automatic modifier calculation
- Hit points, armor class, and combat stats
- Inventory and equipment management
- Spellcasting support

### 🧝 NPC Management

- Create and track non-player characters
- Manage relationships and locations
- Store descriptions and notes

### 🗺️ Location/World Building

- Create detailed locations (cities, dungeons, etc.)
- Track populations, governments, and notable features
- Connect locations and manage geography

### ❗ Quest Management

- Create quests with objectives and rewards
- Track quest status and completion
- Link quests to NPCs and locations

### ⚔️ Combat Management

- Initiative tracking
- Turn-based combat flow
- Combat encounter planning

### ⏰ Session Management

- Session notes and summaries
- Experience and treasure tracking
- Character attendance

### 🏕️ Adventure Log

- Comprehensive event logging
- Categorized by event type (combat, roleplay, exploration, etc.)
- Searchable and filterable
- Importance ratings

### 🚦 Game State Tracking

- Current location and session
- Party level and funds
- Combat status
- In-game date tracking

### 🎲 Utility Tools

- Dice rolling with advantage/disadvantage
- Experience point calculations
- D&D 5e mechanics support

## 💾 Installation

### Prerequisites

- Python 3.10+
- FastMCP 2.8.0+

### Install with FastMCP CLI (Recommended)

```bash
# Install FastMCP
pip install fastmcp>=2.8.0

# Install this server
fastmcp install src/gamemaster_mcp/main.py:mcp -n "D&D Campaign Manager"
```

### Manual Installation

```bash
# Clone repository
git clone https://www.github.com/study-flamingo/gamemaster-mcp.git
cd gamemaster-mcp

# Create virtual environment
uv venv

# Install dependencies
uv sync

# Install to user/system with uv
uv pip install -e .

# Or, run directly
uv run --directory path/to/local/install/src/main.py
```

## 🏁 Usage

### Running with FastMCP CLI (Recommended)

```bash
# Run as a python package
uv run gamemaster-mcp

# Alternatively:
uv run --directory path/to/local/install/src/main.py

# Or, if installed to user/system packages:
uv run gamemaster-mcp

or 

python -m gamemaster_mcp
```

### Traditional Python

```bash
# Run server directly
python -m gamemaster_mcp

# Or using the main script
python src/main.py
```

### Claude Desktop Configuration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "dnd-campaign-manager": {
      "command": "fastmcp",
      "args": ["run", "/path/to/dnd-mcp/src/gamemaster_mcp/main.py"]
    }
  }
}
```

Or with dependencies:

```json
{
  "mcpServers": {
    "dnd-campaign-manager": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "/path/to/dnd-mcp/src/gamemaster_mcp/main.py"
      ]
    }
  }
}
```

## Available Tools (25+ FastMCP Tools)

### Campaign Management

- `create_campaign` - Create a new campaign
- `get_campaign_info` - Get current campaign information  
- `list_campaigns` - List all available campaigns
- `load_campaign` - Switch to a different campaign

### Character Management

- `create_character` - Create a new player character
- `get_character` - Get character sheet details
- `update_character_hp` - Update character hit points
- `add_item_to_character` - Add items to inventory
- `list_characters` - List all characters

### NPC Management

- `create_npc` - Create a new NPC
- `get_npc` - Get NPC details
- `list_npcs` - List all NPCs

### Location Management

- `create_location` - Create a new location
- `get_location` - Get location details
- `list_locations` - List all locations

### Quest Management

- `create_quest` - Create a new quest
- `update_quest` - Update quest status or objectives
- `list_quests` - List quests (optionally filtered by status)

### Game State Management

- `update_game_state` - Update current game state
- `get_game_state` - Get current game state

### Combat Management

- `start_combat` - Initialize combat with initiative order
- `end_combat` - End combat encounter
- `next_turn` - Advance to next participant's turn

### Session Management

- `add_session_note` - Add session notes and summary
- `get_sessions` - Get all session notes

### Adventure Log

- `add_event` - Add event to adventure log
- `get_events` - Get events (with filtering and search)

### Utility Tools

- `roll_dice` - Roll dice with D&D notation (e.g., "1d20", "3d6+2")
- `calculate_experience` - Calculate XP distribution for encounters

## 🖥️ Development

### FastMCP Development Workflow

```bash
# Install development dependencies
uv sync --dev

# Run with [improved MCP inspector](https://www.github.com/mcpjam/inspector)
npx @mcpjam/inspector

# Run tests
pytest
```

## ✈️ Migration from Raw MCP SDK

This server has been migrated from the raw MCP SDK to FastMCP 2.8.0+ for:

- **Simplified Development** - Decorator-based instead of manual tool registration
- **Better Type Safety** - Automatic schema generation from type hints  
- **Enhanced DX** - Built-in development tools and CLI
- **Modern Standards** - Compliance with latest MCP best practices

## 📜 License

MIT License
