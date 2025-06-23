#!/usr/bin/env python3
"""
Example script demonstrating D&D MCP Server functionality with FastMCP 2.8.0+.
This can be used for testing the server components locally.
"""

import asyncio
from gamemaster_mcp.storage import DnDStorage
from gamemaster_mcp.models import (
    Character, NPC, Location, Quest, AdventureEvent, EventType,
    CharacterClass, Race, AbilityScore
)

async def demo():
    """Demonstrate the D&D MCP Server functionality."""
    print("🐉 D&D MCP Server Demo (FastMCP 2.8.0+)")
    print("=" * 50)
    
    # Initialize storage
    storage = DnDStorage("demo_data")
    
    # Create a campaign
    print("\n📚 Creating Campaign...")
    campaign = storage.create_campaign(
        name="Demo Campaign",
        description="A demonstration campaign for the D&D MCP Server with FastMCP 2.8.0+",
        dm_name="Demo DM",
        setting="Forgotten Realms"
    )
    print(f"✅ Created campaign: {campaign.name}")
    
    # Create a character
    print("\n⚔️ Creating Character...")
    character = Character(
        name="Gandalf the Grey",
        player_name="Demo Player",
        character_class=CharacterClass(name="Wizard", level=5),
        race=Race(name="Human"),
        background="Sage",
        alignment="Neutral Good",
        abilities={
            "strength": AbilityScore(score=10),
            "dexterity": AbilityScore(score=14),
            "constitution": AbilityScore(score=12),
            "intelligence": AbilityScore(score=18),
            "wisdom": AbilityScore(score=16),
            "charisma": AbilityScore(score=13),
        },
        hit_points_max=35,
        hit_points_current=35,
        armor_class=12
    )
    storage.add_character(character)
    print(f"✅ Created character: {character.name} (Level {character.character_class.level} {character.race.name} {character.character_class.name})")
    
    # Create an NPC
    print("\n👤 Creating NPC...")
    npc = NPC(
        name="Elara the Innkeeper",
        description="A friendly halfling who runs the local tavern",
        race="Halfling",
        occupation="Innkeeper",
        location="Greenhill Tavern",
        attitude="friendly"
    )
    storage.add_npc(npc)
    print(f"✅ Created NPC: {npc.name}")
    
    # Create a location
    print("\n🏰 Creating Location...")
    location = Location(
        name="Greenhill Village",
        location_type="Village",
        description="A small, peaceful village nestled in rolling green hills",
        population=150,
        government="Council of Elders",
        notable_features=["Ancient Oak Tree", "Stone Bridge", "Weekly Market"]
    )
    storage.add_location(location)
    print(f"✅ Created location: {location.name}")
    
    # Create a quest
    print("\n📜 Creating Quest...")
    quest = Quest(
        title="The Missing Merchant",
        description="A local merchant has gone missing on the road to the capital",
        giver="Elara the Innkeeper",
        objectives=[
            "Investigate the merchant's last known location",
            "Find clues about what happened",
            "Rescue the merchant or discover his fate"
        ],
        reward="100 gold pieces and a magic item"
    )
    storage.add_quest(quest)
    print(f"✅ Created quest: {quest.title}")
    
    # Add some events
    print("\n📝 Adding Adventure Events...")
    events = [
        AdventureEvent(
            event_type=EventType.ROLEPLAY,
            title="Meeting at the Tavern",
            description="The party meets Elara and learns about the missing merchant",
            location="Greenhill Tavern",
            characters_involved=["Gandalf the Grey"],
            importance=3
        ),
        AdventureEvent(
            event_type=EventType.EXPLORATION,
            title="Investigating the Road",
            description="The party searches the road where the merchant disappeared",
            characters_involved=["Gandalf the Grey"],
            importance=4
        ),
        AdventureEvent(
            event_type=EventType.COMBAT,
            title="Bandit Ambush",
            description="The party is attacked by bandits who reveal information about the merchant",
            characters_involved=["Gandalf the Grey"],
            importance=4
        )
    ]
    
    for event in events:
        storage.add_event(event)
        print(f"  📖 Added {event.event_type} event: {event.title}")
    
    # Update game state
    print("\n🎮 Updating Game State...")
    storage.update_game_state(
        current_location="Greenhill Village",
        current_session=1,
        party_level=5,
        party_funds="250 gp"
    )
    print("✅ Updated game state")
    
    # Display summary
    print("\n" + "=" * 50)
    print("📊 Campaign Summary")
    print("=" * 50)
    
    current_campaign = storage.get_current_campaign()
    print(f"Campaign: {current_campaign.name}")
    print(f"Characters: {len(current_campaign.characters)}")
    print(f"NPCs: {len(current_campaign.npcs)}")
    print(f"Locations: {len(current_campaign.locations)}")
    print(f"Quests: {len(current_campaign.quests)}")
    
    game_state = storage.get_game_state()
    print(f"Current Location: {game_state.current_location}")
    print(f"Party Level: {game_state.party_level}")
    print(f"Party Funds: {game_state.party_funds}")
    
    events = storage.get_events(limit=5)
    print(f"Recent Events: {len(events)}")
    
    print("\n🎉 Demo completed! Check the 'demo_data' directory for saved files.")
    print("\n🚀 To run the FastMCP 2.8.0+ compliant server:")
    print("   python -m gamemaster_mcp")
    print("   or: fastmcp dev src/gamemaster_mcp/main.py:mcp")

if __name__ == "__main__":
    asyncio.run(demo())
