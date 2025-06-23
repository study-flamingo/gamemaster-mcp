# D&D MCP Server - FastMCP 2.8.0+ Compliant

A comprehensive Model Context Protocol (MCP) server for managing Dungeons & Dragons campaigns, built with **FastMCP 2.8.0+** for modern compatibility and enhanced performance.

## 🎯 FastMCP 2.8.0+ Compliance

This server is fully compliant with **FastMCP 2.8.0+** and includes:

✅ **Modern Decorator-Based Architecture** - Uses `@mcp.tool` decorators  
✅ **Automatic Schema Generation** - From Python type annotations  
✅ **Pydantic Field Validation** - Rich parameter validation and descriptions  
✅ **FastMCP CLI Support** - Easy installation and development  
✅ **Type Safety** - Full type hints with mypy compatibility  

## Features

### Campaign Management
- Create and manage multiple campaigns
- Switch between campaigns seamlessly
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
git clone <repository-url>
cd dnd-mcp

# Install dependencies
pip install -e .

# Or install with uv
uv pip install -e .
```

## Usage

### Running with FastMCP CLI (Recommended)

```bash
# Development mode with inspector
fastmcp dev src/gamemaster_mcp/main.py:mcp

# Run demo to test functionality
python demo.py
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
      "args": ["run", "/path/to/dnd-mcp/src/gamemaster_mcp/main.py:mcp"]
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
        "--with", "fastmcp>=2.8.0",
        "--with", "pydantic>=2.0.0",
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

## FastMCP 2.8.0+ Features

### Type-Safe Tool Definitions

```python
@mcp.tool
def create_character(
    name: Annotated[str, Field(description="Character name")],
    character_class: Annotated[str, Field(description="Character class")],
    class_level: Annotated[int, Field(description="Class level", ge=1, le=20)],
    race: Annotated[str, Field(description="Character race")],
    # ... more parameters with rich validation
) -> str:
    """Create a new player character."""
    # Implementation automatically handled by FastMCP
```

### Automatic Schema Generation

FastMCP automatically generates JSON schemas from your Python type annotations, providing:
- Parameter validation
- Rich descriptions for LLMs
- Constraint enforcement (ge, le, pattern, etc.)
- Optional vs required parameter detection

### Rich Parameter Validation

```python
strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10
attitude: Annotated[Optional[Literal["friendly", "neutral", "hostile"]], Field(...)] = None
```

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

### Creating a Campaign with FastMCP

```python
# FastMCP automatically handles this as a tool
result = await mcp_client.call_tool("create_campaign", {
    "name": "Curse of Strahd",
    "description": "A gothic horror adventure in Barovia",
    "dm_name": "John Smith",
    "setting": "Ravenloft"
})
```

### Creating a Character

```python
result = await mcp_client.call_tool("create_character", {
    "name": "Gandalf the Grey",
    "character_class": "Wizard",
    "class_level": 5,
    "race": "Human",
    "strength": 10,
    "intelligence": 18,
    "wisdom": 16
})
```

### Rolling Dice

```python
result = await mcp_client.call_tool("roll_dice", {
    "dice_notation": "1d20+5",
    "advantage": True
})
```

## Development

### FastMCP Development Workflow

```bash
# Install development dependencies
pip install -e .[dev]

# Run with FastMCP inspector
fastmcp dev src/gamemaster_mcp/main.py:mcp

# Run tests
pytest

# Type checking
mypy src/

# Code formatting
black src/
ruff check src/
```

### Adding New Tools

With FastMCP 2.8.0+, adding tools is simple:

```python
@mcp.tool
def new_tool(
    param: Annotated[str, Field(description="Parameter description")]
) -> str:
    """Tool description for the LLM."""
    # Your implementation
    return "Result"
```

FastMCP automatically:
- Registers the tool
- Generates JSON schema
- Handles parameter validation
- Routes requests to your function

## Compliance Features

### FastMCP 2.8.0+ Specific
- ✅ Modern import syntax: `from fastmcp import FastMCP`
- ✅ Decorator-based tools: `@mcp.tool`
- ✅ Automatic schema generation from type hints
- ✅ Rich parameter validation with Pydantic
- ✅ FastMCP CLI integration
- ✅ Built-in development server

### Type Safety
- ✅ Full type annotations
- ✅ Pydantic model validation
- ✅ MyPy compatibility
- ✅ Runtime type checking

### Modern Python
- ✅ Python 3.10+ features
- ✅ `Annotated` type hints
- ✅ `Literal` types for constraints
- ✅ Modern async/await patterns

## Migration from Raw MCP SDK

This server has been migrated from the raw MCP SDK to FastMCP 2.8.0+ for:
- **Simplified Development** - Decorator-based instead of manual tool registration
- **Better Type Safety** - Automatic schema generation from type hints  
- **Enhanced DX** - Built-in development tools and CLI
- **Modern Standards** - Compliance with latest MCP best practices

## License

MIT License

---

**FastMCP 2.8.0+ Compliant** ✅ | **D&D 5e Compatible** 🐉 | **Production Ready** 🚀
