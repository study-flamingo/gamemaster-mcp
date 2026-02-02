# Split Storage Integration Summary

## Overview

This document summarizes the integration of `SplitStorageBackend` into the main `DnDStorage` (formerly `CampaignStorage`) class, completed as part of Issue #4.

## Changes Made

### 1. DnDStorage Initialization

**File**: `src/gamemaster_mcp/storage.py` (lines 68-69)

Added initialization of the split storage backend without auto-loading campaigns to prevent double-loading:

```python
# Initialize split storage backend (without auto-loading campaigns)
self._split_backend = SplitStorageBackend(data_dir=data_dir, auto_load=False)
```

### 2. SplitStorageBackend Constructor

**File**: `src/gamemaster_mcp/storage.py` (line 733)

Modified `SplitStorageBackend.__init__` to accept an `auto_load` parameter:

```python
def __init__(self, data_dir: str | Path = "dnd_data", auto_load: bool = True):
```

This prevents the backend from automatically loading campaigns when used as a backend for DnDStorage.

### 3. Campaign Creation (create_campaign)

**File**: `src/gamemaster_mcp/storage.py` (lines 293-316)

Modified to use split storage backend for all new campaigns:

```python
def create_campaign(self, name: str, description: str, dm_name: str | None = None, setting: str | Path | None = None) -> Campaign:
    """Create a new campaign using split storage format."""
    # Use split backend to create the campaign
    campaign = self._split_backend.create_campaign(
        name=name,
        description=description,
        dm_name=dm_name,
        setting=setting
    )

    # Sync to main storage
    self._current_campaign = campaign
    self._current_format = StorageFormat.SPLIT

    # Rebuild indexes for new campaign
    self._rebuild_character_index()

    # Update campaign hash
    self._campaign_hash = self._compute_campaign_hash()

    return campaign
```

### 4. Split Campaign Saving (_save_split_campaign)

**File**: `src/gamemaster_mcp/storage.py` (lines 202-215)

Implemented to delegate saving to the split backend:

```python
def _save_split_campaign(self) -> None:
    """Save campaign using split directory structure (new format)."""
    if not self._current_campaign:
        return

    # Sync current campaign to split backend
    self._split_backend._current_campaign = self._current_campaign

    # Use split backend to save all files
    self._split_backend.save_all(force=False)
```

### 5. Split Campaign Loading (_load_split_campaign)

**File**: `src/gamemaster_mcp/storage.py` (lines 381-389)

Implemented to delegate loading to the split backend:

```python
def _load_split_campaign(self, name: str) -> Campaign:
    """Load a campaign from split directory structure (new format)."""
    # Use split backend to load campaign
    campaign = self._split_backend.load_campaign(name)
    return campaign
```

### 6. Campaign Loading (load_campaign)

**File**: `src/gamemaster_mcp/storage.py` (lines 345-367)

Modified to sync the split backend when loading split campaigns:

```python
elif storage_format == StorageFormat.SPLIT:
    campaign = self._load_split_campaign(name)
    # Sync split backend with loaded campaign
    self._split_backend._current_campaign = campaign
```

### 7. Batch Updates (batch_update)

**File**: `src/gamemaster_mcp/storage.py` (lines 143-151)

Modified to sync with split backend during batch operations:

```python
@contextmanager
def batch_update(self):
    """Context manager for batch operations - defers saves until exit."""
    self._batch_mode = True
    try:
        yield
        # Sync with split backend if using split format
        if self._current_format == StorageFormat.SPLIT and self._current_campaign:
            self._split_backend._current_campaign = self._current_campaign
        self._save_campaign(force=True)
    finally:
        self._batch_mode = False
```

### 8. Format Detection Fixes

**File**: `src/gamemaster_mcp/storage.py`

Fixed all references from `metadata.json` to `campaign.json` to match the actual split storage file structure:

- `_detect_campaign_format()` (lines 103-106)
- `_load_current_campaign()` (lines 238-242)
- `list_campaigns()` (lines 334-337)

## Architecture

### Storage Flow

```
DnDStorage (Main Interface)
    ├── create_campaign() → SplitStorageBackend.create_campaign()
    ├── _save_campaign()
    │   ├── MONOLITHIC → _save_monolithic_campaign()
    │   └── SPLIT → _save_split_campaign() → SplitStorageBackend.save_all()
    └── load_campaign()
        ├── MONOLITHIC → _load_monolithic_campaign()
        └── SPLIT → _load_split_campaign() → SplitStorageBackend.load_campaign()
```

### Data Synchronization

The integration maintains synchronization between `DnDStorage` and `SplitStorageBackend`:

1. **On Create**: Split backend creates campaign, DnDStorage syncs and builds indexes
2. **On Save**: DnDStorage syncs campaign to backend before saving
3. **On Load**: Backend loads campaign, DnDStorage syncs and builds indexes
4. **On Batch Update**: DnDStorage syncs to backend before final save

## Compatibility

### New Campaigns
- All new campaigns use split storage format automatically
- Directory structure created with separate JSON files
- Per-file dirty tracking for efficient saves

### Existing Campaigns
- Monolithic campaigns continue to work unchanged
- Automatic format detection on load
- No migration required - campaigns stay in their original format

### Mixed Environment
- Can have both monolithic and split campaigns in the same data directory
- `list_campaigns()` finds and lists both formats
- Auto-load picks the most recently modified campaign regardless of format

## Testing

### Test Files Created

1. **test_storage_integration.py**: Comprehensive integration tests
   - Tests new campaign creation with split format
   - Tests character operations (add, update, remove)
   - Tests batch updates
   - Tests character index rebuilding
   - Tests loading split campaigns
   - Tests all entity types (NPCs, locations, quests)
   - Tests campaign listing

2. **test_manual_integration.py**: Manual verification script
   - Simple end-to-end test
   - Can be run directly with Python
   - Verifies key functionality

### Test Coverage

The integration tests verify:
- ✓ New campaigns use split format
- ✓ Directory structure created correctly
- ✓ Characters saved to split storage
- ✓ Character updates persist
- ✓ Character removal works
- ✓ Batch updates work correctly
- ✓ Character indexes work (by ID, name, player name)
- ✓ Campaign loading works
- ✓ NPCs, locations, quests work with split storage
- ✓ Campaign listing includes split campaigns
- ✓ Most recent campaign loading works

## Key Features Preserved

All existing DnDStorage features continue to work with split storage:

1. **Character Management**
   - Add, update, remove, get, list
   - O(1) lookups by ID, name, or player name
   - Character index rebuilding

2. **Batch Mode**
   - Deferred saves during bulk operations
   - Single save at the end
   - Works with split storage

3. **Dirty Tracking**
   - Per-file hashing in split storage
   - Only modified files are written
   - Efficient incremental saves

4. **All Entity Types**
   - Characters, NPCs, locations, quests
   - Combat encounters, session notes
   - Game state management

## Performance Benefits

Split storage provides several advantages:

1. **Faster Saves**: Only modified sections are written
2. **Better Version Control**: Changes to one entity type don't affect others
3. **Reduced Memory**: Can load individual sections as needed (future optimization)
4. **Easier Debugging**: Separate files for each data category

## Future Enhancements

Potential improvements that could be added:

1. **Migration Tool**: Convert monolithic campaigns to split format
2. **Lazy Loading**: Load entity sections on-demand
3. **Compression**: Compress individual section files
4. **Backup/Export**: Easier backup of specific campaign sections

## Files Modified

- `src/gamemaster_mcp/storage.py` - Main integration changes
- `test_storage_integration.py` - Integration test suite (new)
- `test_manual_integration.py` - Manual test script (new)

## Commit History

All changes committed with prefix "Issue #4:" for traceability.
