# Changelog

All notable changes to Gamemaster MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2025-02-01

### Added
- `delete_character` tool to remove characters from campaigns
- Character lookup now supports searching by player name in addition to character name and ID
- `bulk_update_characters` tool for applying changes to multiple characters at once (e.g., area damage)
- CHANGELOG.md to track project changes

### Fixed
- Character lookup returning `None` when found by ID

### Changed
- Updated README.md to document `delete_character` tool

## [0.1.0] - 2024-12-01

### Added
- Initial release of Gamemaster MCP
- **Campaign Management**
  - `create_campaign` - Create a new D&D campaign
  - `get_campaign_info` - Get current campaign information
  - `list_campaigns` - List all available campaigns
  - `load_campaign` - Switch to a different campaign
- **Character Management**
  - `create_character` - Create a new player character with full D&D 5e stats
  - `get_character` - Get character sheet details
  - `update_character` - Update character properties (name, stats, HP, etc.)
  - `add_item_to_character` - Add items to inventory
  - `list_characters` - List all characters
  - Ability scores with automatic modifier calculation
  - Hit points, armor class, and combat stats
  - Inventory and equipment management
  - Spellcasting support
- **NPC Management**
  - `create_npc` - Create a new NPC
  - `get_npc` - Get NPC details
  - `list_npcs` - List all NPCs
  - Public descriptions and private bios for DM secrets
  - Attitude tracking (friendly, neutral, hostile, unknown)
- **Location Management**
  - `create_location` - Create a new location
  - `get_location` - Get location details
  - `list_locations` - List all locations
  - Support for various location types (city, town, village, dungeon, etc.)
  - Population, government, and notable features tracking
- **Quest Management**
  - `create_quest` - Create a new quest
  - `update_quest` - Update quest status or objectives
  - `list_quests` - List quests with optional status filter
  - Quest status tracking (active, completed, failed, on_hold)
  - Individual objective completion
- **Combat Management**
  - `start_combat` - Initialize combat with initiative order
  - `end_combat` - End combat encounter
  - `next_turn` - Advance to next participant's turn
  - Automatic initiative sorting
- **Game State Tracking**
  - `update_game_state` - Update current game state
  - `get_game_state` - Get current game state
  - Current location and session tracking
  - Party level and funds
  - In-game date tracking
  - Combat status
- **Session Management**
  - `add_session_note` - Add session notes and summary
  - `get_sessions` - Get all session notes
  - Experience and treasure tracking
  - Character attendance
- **Adventure Log**
  - `add_event` - Add event to adventure log
  - `get_events` - Get events with filtering and search
  - Event types: combat, roleplay, exploration, quest, character, world, session
  - Importance ratings (1-5)
  - Searchable and filterable
- **Utility Tools**
  - `roll_dice` - Roll dice with D&D notation (e.g., "1d20", "3d6+2")
  - `calculate_experience` - Calculate XP distribution for encounters
  - Advantage/disadvantage support for d20 rolls

[Unreleased]: https://github.com/study-flamingo/gamemaster-mcp/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/study-flamingo/gamemaster-mcp/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/study-flamingo/gamemaster-mcp/releases/tag/v0.1.0
