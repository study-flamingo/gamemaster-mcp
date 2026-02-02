#!/usr/bin/env python3
"""
Manual integration test for split storage.
Run this script to verify the integration works correctly.
"""

import tempfile
import shutil
from pathlib import Path

from gamemaster_mcp.storage import DnDStorage, StorageFormat
from gamemaster_mcp.models import Character, CharacterClass, Race, AbilityScore


def test_basic_integration():
    """Test basic split storage integration."""
    print("Testing split storage integration...")

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    print(f"Using temp directory: {temp_dir}")

    try:
        # Test 1: Create new campaign
        print("\n1. Creating new campaign...")
        storage = DnDStorage(data_dir=temp_dir)
        campaign = storage.create_campaign(
            name="Test Campaign",
            description="Integration test campaign"
        )
        print(f"   ✓ Campaign created: {campaign.name}")
        print(f"   ✓ Storage format: {storage._current_format}")

        # Verify it's using split format
        assert storage._current_format == StorageFormat.SPLIT, "Should use split format"
        print("   ✓ Using split format")

        # Verify directory structure
        campaign_dir = Path(temp_dir) / "campaigns" / "Test Campaign"
        assert campaign_dir.exists(), "Campaign directory should exist"
        assert (campaign_dir / "campaign.json").exists(), "campaign.json should exist"
        assert (campaign_dir / "characters.json").exists(), "characters.json should exist"
        print("   ✓ Directory structure verified")

        # Test 2: Add character
        print("\n2. Adding character...")
        char = Character(
            name="Gandalf",
            player_name="John",
            character_class=CharacterClass(name="Wizard", level=10, hit_dice="1d6"),
            race=Race(name="Human"),
            abilities={
                "strength": AbilityScore(score=10),
                "dexterity": AbilityScore(score=12),
                "constitution": AbilityScore(score=14),
                "intelligence": AbilityScore(score=20),
                "wisdom": AbilityScore(score=16),
                "charisma": AbilityScore(score=15),
            }
        )
        storage.add_character(char)
        print(f"   ✓ Character added: {char.name}")

        # Verify character was saved
        import json
        with open(campaign_dir / "characters.json", 'r') as f:
            data = json.load(f)
        assert "Gandalf" in data, "Character should be in characters.json"
        print("   ✓ Character saved to split storage")

        # Test 3: Reload campaign
        print("\n3. Reloading campaign...")
        new_storage = DnDStorage(data_dir=temp_dir)
        new_storage.load_campaign("Test Campaign")
        print(f"   ✓ Campaign loaded: {new_storage._current_campaign.name}")
        print(f"   ✓ Storage format: {new_storage._current_format}")

        # Verify character loaded
        loaded_char = new_storage.get_character("Gandalf")
        assert loaded_char is not None, "Character should be loaded"
        assert loaded_char.name == "Gandalf", "Character name should match"
        print(f"   ✓ Character loaded: {loaded_char.name}")

        # Test 4: Update character
        print("\n4. Updating character...")
        new_storage.update_character("Gandalf", level=15)
        updated_char = new_storage.get_character("Gandalf")
        assert updated_char.character_class.level == 15, "Level should be updated"
        print("   ✓ Character updated")

        # Test 5: Character lookup by ID
        print("\n5. Testing character lookup by ID...")
        char_by_id = new_storage.get_character(char.id)
        assert char_by_id is not None, "Should find character by ID"
        assert char_by_id.name == "Gandalf", "Should be correct character"
        print(f"   ✓ Found character by ID: {char_by_id.name}")

        # Test 6: Character lookup by player name
        print("\n6. Testing character lookup by player name...")
        char_by_player = new_storage.get_character("John")
        assert char_by_player is not None, "Should find character by player name"
        assert char_by_player.name == "Gandalf", "Should be correct character"
        print(f"   ✓ Found character by player name: {char_by_player.name}")

        print("\n✅ All tests passed!")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up temp directory: {temp_dir}")


if __name__ == "__main__":
    test_basic_integration()
