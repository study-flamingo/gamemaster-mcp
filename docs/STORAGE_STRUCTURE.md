# D&D MCP Server - Data Storage Guide

This guide details the file and folder structure used by the D&D MCP Server to persist campaign data. All data is managed by the `DnDStorage` class located in `src/gamemaster_mcp/storage.py`.

## Root Directory

By default, all application data is stored in a root directory named `dnd_data/`. This folder is created automatically in the directory from which the server is run.

```
dnd_data/
├── campaigns/
└── events/
```

## Campaigns Directory

- **Path**: `dnd_data/campaigns/`
- **Purpose**: This directory stores all individual campaign files.

Each campaign is saved as a single, self-contained JSON file. The `DnDStorage` class's `_save_campaign` method serializes the entire `Campaign` Pydantic model, including all associated characters, NPCs, locations, quests, and the game state, into this file.

### File Naming

The filename for each campaign is derived from the campaign name provided during creation. The `_get_campaign_file` method sanitizes the name to ensure it's safe for the filesystem (allowing only alphanumeric characters, spaces, hyphens, and underscores) and appends a `.json` extension.

**Example**: A campaign named "The Dragon's Curse!" would be saved as:

```
dnd_data/
└── campaigns/
    └── The Dragons Curse.json
```

## Events Directory

- **Path**: `dnd_data/events/`
- **Purpose**: This directory stores the global adventure log.

Unlike campaign-specific data, adventure events are stored in a single, global file. This allows for a persistent timeline of major events across all campaigns managed by the server.

### File Naming

The events log is always stored in a file named `adventure_log.json`. The `_get_events_file` method hardcodes this path. The file contains a JSON array of all `AdventureEvent` objects.

```
dnd_data/
└── events/
    └── adventure_log.json
```

## Summary of Data Structure

| Path                            | Content                                                                                             | Managed By Methods                                                              |
| ------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `dnd_data/`                     | The root directory for all persistent application data.                                             | `DnDStorage.__init__`                                                           |
| `dnd_data/campaigns/`           | A subdirectory containing all individual campaign save files.                                       | `DnDStorage.__init__`                                                           |
| `dnd_data/campaigns/*.json`     | A JSON file representing a single, complete `Campaign` object and all its nested data.              | `_get_campaign_file`, `_save_campaign`, `_load_current_campaign`, `load_campaign` |
| `dnd_data/events/`              | A subdirectory for global, cross-campaign data.                                                     | `DnDStorage.__init__`                                                           |
| `dnd_data/events/adventure_log.json` | A JSON file containing a list of all `AdventureEvent` objects, forming a global adventure log. | `_get_events_file`, `_save_events`, `_load_events`                              |
