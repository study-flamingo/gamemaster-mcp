# Migration Utility Scripts

This directory contains utility scripts for the Gamemaster MCP project.

## migrate_campaign.py

Convert monolithic campaign files (single JSON) to the new split directory structure (multiple files).

### Quick Start

```bash
# See what would happen (recommended first step)
python scripts/migrate_campaign.py "My Campaign" --dry-run

# Migrate with backup (safest option)
python scripts/migrate_campaign.py "My Campaign" --backup
```

### Why Migrate?

The split format offers several advantages:

1. **Better Version Control**: Git diffs are cleaner when data is split
2. **Easier Collaboration**: Multiple people can edit different sections
3. **Performance**: Only modified sections are written to disk
4. **Organization**: Clearer structure makes data easier to find

### Directory Structure

**Before (Monolithic):**
```
data/campaigns/
└── My Campaign.json  (single large file)
```

**After (Split):**
```
data/campaigns/
└── My Campaign/
    ├── campaign.json      (metadata only)
    ├── characters.json
    ├── npcs.json
    ├── locations.json
    ├── quests.json
    ├── encounters.json
    ├── game_state.json
    └── sessions/
        ├── session-001.json
        ├── session-002.json
        └── session-003.json
```

### Usage Examples

#### Basic Migration

```bash
# Migrate and keep backup
python scripts/migrate_campaign.py "Campaign Name" --backup

# Migrate and delete original
python scripts/migrate_campaign.py "Campaign Name"
```

#### Advanced Options

```bash
# Preview changes without making them
python scripts/migrate_campaign.py "Campaign Name" --dry-run

# Force overwrite if split directory already exists
python scripts/migrate_campaign.py "Campaign Name" --force

# Use custom data directory
python scripts/migrate_campaign.py "Campaign Name" --data-dir /custom/path
```

#### Real-World Example

```bash
# Step 1: Preview the migration
python scripts/migrate_campaign.py "L'Ombra sulla Terra di Mezzo" --dry-run --data-dir data

# Output shows:
# - What files would be created
# - Size of each file
# - Total data counts

# Step 2: If everything looks good, migrate with backup
python scripts/migrate_campaign.py "L'Ombra sulla Terra di Mezzo" --backup --data-dir data

# Result:
# - New split directory created
# - Original file renamed to .json.bak
# - Server automatically uses new format
```

### Options Reference

| Option | Short | Description |
|--------|-------|-------------|
| `--backup` | - | Keep original file as `.json.bak` |
| `--dry-run` | - | Show what would happen without making changes |
| `--force` | - | Overwrite existing split directory |
| `--data-dir` | - | Specify data directory (default: `dnd_data`) |

### Safety Features

1. **Validation**: Checks all inputs before making changes
2. **Atomic Writes**: Uses temp files to prevent corruption
3. **Rollback**: Automatically undoes changes if migration fails
4. **Dry-Run**: Preview mode lets you see changes first

### Error Handling

The script handles common errors gracefully:

- **Missing file**: Clear error message with file path
- **Invalid JSON**: Reports JSON syntax errors
- **Missing fields**: Lists required fields that are missing
- **Permission errors**: Reports file access issues
- **Existing directory**: Prevents accidental overwrites (use `--force`)

### Migration Process

1. **Validation**: Verify inputs and check for conflicts
2. **Load**: Read and parse monolithic campaign file
3. **Create**: Build split directory structure
4. **Extract**: Write individual JSON files for each section
5. **Cleanup**: Backup or remove original file

If any step fails, all changes are automatically rolled back.

### Testing

The migration utility has comprehensive test coverage:

```bash
# Run all migration tests
uv run pytest tests/test_migrate_campaign.py -v

# Run specific test
uv run pytest tests/test_migrate_campaign.py::TestCampaignMigrator::test_migration_creates_all_files -v
```

### Troubleshooting

#### "Campaign file not found"
- Check campaign name matches exactly (case-sensitive)
- Verify data directory path is correct
- Use `--data-dir` if not using default location

#### "Split directory already exists"
- Use `--force` to overwrite
- Or manually remove/rename existing directory
- Or use different campaign name

#### "Invalid JSON"
- Original file may be corrupted
- Try opening in text editor to check syntax
- Use JSON validator online

#### "Permission denied"
- Check file/directory permissions
- Try running with appropriate user rights
- Ensure disk space is available

### Best Practices

1. **Always start with `--dry-run`**: Preview changes first
2. **Use `--backup` for first migration**: Keep original safe
3. **Verify split files**: Check that data looks correct after migration
4. **Test with small campaign first**: Gain confidence before migrating large campaigns
5. **Keep backups**: Even with `--backup`, consider manual copies of important campaigns

### Future Enhancements

Potential improvements for future versions:

- **Batch migration**: Migrate multiple campaigns at once
- **Progress bars**: Visual feedback for large campaigns
- **Data validation**: Verify data integrity after migration
- **Compression**: Optional compression for large campaigns
- **Reverse migration**: Convert split back to monolithic if needed

### Support

For issues or questions:
- Check the main README.md for project documentation
- Review test cases for usage examples
- Open an issue on GitHub with error details
