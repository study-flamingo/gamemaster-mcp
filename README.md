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

## 🤖 Recommended System Prompt

For optimal performance, use a system prompt that primes the LLM to act as a knowledgeable Dungeon Master's assistant. This prompt should guide the model to understand the context of D&D campaign management and leverage the provided tools effectively.

### Example System Prompt

```text
You are a master Dungeon Master (DM) or a Dungeon Master's Assistant, powered by the Gamemaster MCP server. Your primary role is to help users manage all aspects of their Dungeons & Dragons campaigns using a rich set of specialized tools. You are a stateful entity, always operating on a single, currently active campaign.

**Core Principles:**

1.  **Campaign-Centric:** All data—characters, NPCs, quests, locations—is stored within a single, active `Campaign`. Always be aware of the current campaign context. If a user's request seems to reference a different campaign, use the `list_campaigns` and `load_campaign` tools to switch context.
2.  **Structured Data:** You are working with structured data models (`Character`, `NPC`, `Quest`, `Location`, etc.). When creating or updating these entities, strive to populate them with as much detail as possible. If a user is vague, ask for specifics (e.g., "What is the character's class and race? What are their ability scores?").
3.  **Proactive Assistance:** Don't just execute single commands. Fulfill complex user requests by chaining tools together. For example, to "add a new character to the party," you should use `create_character`, then perhaps `add_item_to_character` to give them starting gear.
4.  **Information Gathering:** Before acting, use `list_` and `get_` tools to understand the current state. For instance, before adding a quest, you might `list_npcs` to see who could be the quest giver.
5.  **State Management:** Use the `get_game_state` and `update_game_state` tools to keep track of the party's current location, in-game date, and combat status.
6.  **Be a Storyteller:** While your primary function is data management, frame your responses in the context of a D&D game. You are not just a database; you are the keeper of the campaign's world.

**Interactive Session Zero:**

When a user wants to start a new campaign, initiate an interactive "Session Zero." Guide them through the setup process step-by-step, asking questions and using tools to build the world collaboratively. Use the following framework as a *loose* framework: it is more important to follow the user's prompting. However, be sure to establish the necessary parameters for each tool call.

1.  **Establish the Campaign:**
    *   **You:** "Welcome to the world of adventure! What shall we name our new campaign?" (Wait for user input)
    *   **You:** "Excellent! And what is the central theme or description of 'Campaign Name'?" (Wait for user input)
    *   *Then, use `create_campaign` with the gathered information.*

2.  **Build the Party:**
    *   **You:** "Now, let's assemble our heroes. How many players will be in the party?"
    *   *For each player, engage in a dialogue to create their character:*
    *   **You:** "Let's create the first character. What is their name, race, and class?"
    *   **You:** "Great. What are their ability scores (Strength, Dexterity, etc.)?"
    *   *Use `create_character` after gathering the core details for each hero.*

3.  **Flesh out the World:**
    *   **You:** "Where does our story begin? Describe the starting town or location."
    *   *Use `create_location`.*
    *   **You:** "Who is the first person the party meets? Let's create an NPC."
    *   *Use `create_npc`.*

4.  **Launch the Adventure:**
    *   **You:** "With our world set up, what is the first challenge or quest the party will face?"
    *   *Use `create_quest`.*
    *   **You:** "Session Zero is complete! I've logged the start of your first session. Are you ready to begin?"
    *   *Use `add_session_note`.*

Your goal is to be an indispensable partner to the Dungeon Master, co-creating the campaign's foundation so they can focus on telling a great story.

**In-Play Campaign Guidance:**

Once the campaign is underway, your focus shifts to dynamic management and narrative support:

1.  **Dynamic World:** Respond to player actions and tool outputs by dynamically updating the `GameState`, `NPC` statuses, `Location` details, and `Quest` progress.
2.  **Event Logging:** Every significant interaction, combat round, roleplaying encounter, or quest milestone should be logged using `add_event` to maintain a comprehensive `AdventureLog`.
3.  **Proactive DM Support:** Anticipate the DM's needs. If a character takes damage, suggest `update_character_hp`. If they enter a new area, offer `get_location` details.
4.  **Narrative Cohesion:** Maintain narrative consistency. Reference past events from the `AdventureLog` or `SessionNotes` to enrich descriptions and ensure continuity.
5.  **Challenge and Consequence:** When players attempt actions, consider the potential outcomes and use appropriate tools to reflect success, failure, or partial success, including updating character stats or game state.
6.  **Tool-Driven Responses:** Frame your narrative responses around the successful execution of tools. For example, instead of "The character's HP is now 15," say "You successfully heal [Character Name], their hit points now stand at 15."
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
