#!/usr/bin/env python3
"""
FastMCP 2.8.0+ Compatibility Verification Script
Verifies that the D&D MCP Server is fully compliant with FastMCP 2.8.0+
"""

import asyncio
import sys
from typing import Dict, Any

# Test imports
try:
    from fastmcp import FastMCP, Client
    from pydantic import Field
    from typing import Annotated, Literal, Optional, List
    print("✅ FastMCP 2.8.0+ imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test our server imports
try:
    from gamemaster_mcp.main import mcp
    from gamemaster_mcp.storage import DnDStorage
    from gamemaster_mcp.models import Campaign, Character
    print("✅ D&D MCP Server imports successful")
except ImportError as e:
    print(f"❌ Server import error: {e}")
    sys.exit(1)


async def verify_fastmcp_compliance():
    """Verify FastMCP 2.8.0+ compliance."""
    print("\n🔍 FastMCP 2.8.0+ Compliance Verification")
    print("=" * 50)
    
    # Test 1: Server instance type
    print(f"Server type: {type(mcp)}")
    assert isinstance(mcp, FastMCP), "Server must be FastMCP instance"
    print("✅ Server is FastMCP instance")
    
    # Test 2: Server name and dependencies
    print(f"Server name: {mcp.name}")
    assert mcp.name == "D&D Campaign Manager", "Server name verification"
    print("✅ Server name correct")
    
    print(f"Dependencies: {mcp.dependencies}")
    assert "pydantic>=2.0.0" in mcp.dependencies, "Pydantic dependency required"
    print("✅ Dependencies configured")
    
    # Test 3: Tool registration
    tools = await mcp.get_tools()
    print(f"Registered tools: {len(tools)}")
    
    # Expected tools (from our implementation)
    expected_tools = [
        "create_campaign", "get_campaign_info", "list_campaigns", "load_campaign",
        "create_character", "get_character", "update_character_hp", "add_item_to_character", "list_characters",
        "create_npc", "get_npc", "list_npcs",
        "create_location", "get_location", "list_locations", 
        "create_quest", "update_quest", "list_quests",
        "update_game_state", "get_game_state",
        "start_combat", "end_combat", "next_turn",
        "add_session_note", "get_sessions",
        "add_event", "get_events",
        "roll_dice", "calculate_experience"
    ]
    
    print("\n📋 Tool Verification:")
    for tool_name in expected_tools:
        if tool_name in tools:
            print(f"  ✅ {tool_name}")
        else:
            print(f"  ❌ {tool_name} - MISSING")
    
    missing_tools = set(expected_tools) - set(tools.keys())
    if missing_tools:
        print(f"\n❌ Missing tools: {missing_tools}")
        return False
    
    print(f"\n✅ All {len(expected_tools)} expected tools registered")
    
    # Test 4: Tool schema validation
    print("\n🔍 Tool Schema Verification:")
    sample_tools = ["create_campaign", "create_character", "roll_dice"]
    
    for tool_name in sample_tools:
        tool = tools[tool_name]
        schema = tool.inputSchema
        
        print(f"\n  Tool: {tool_name}")
        print(f"    Description: {tool.description[:50]}...")
        print(f"    Parameters: {len(schema.get('properties', {}))}")
        
        # Verify schema has required properties
        assert "type" in schema, f"{tool_name} schema missing type"
        assert "properties" in schema, f"{tool_name} schema missing properties"
        
        # Check for proper parameter descriptions
        for param_name, param_schema in schema.get("properties", {}).items():
            assert "description" in param_schema, f"{tool_name}.{param_name} missing description"
        
        print(f"    ✅ Schema valid")
    
    # Test 5: Client interaction test
    print("\n🔗 Client Interaction Test:")
    try:
        async with Client(mcp) as client:
            # Test a simple tool call
            result = await client.call_tool("get_campaign_info", {})
            print(f"    Campaign info result: {result[0].text[:50]}...")
            print("    ✅ Client interaction successful")
    except Exception as e:
        print(f"    ❌ Client interaction failed: {e}")
        return False
    
    return True


async def test_tool_functionality():
    """Test actual tool functionality."""
    print("\n🛠️ Tool Functionality Test")
    print("=" * 30)
    
    try:
        async with Client(mcp) as client:
            # Test 1: Create campaign
            result = await client.call_tool("create_campaign", {
                "name": "Test Campaign",
                "description": "A test campaign for verification"
            })
            print("✅ create_campaign:", result[0].text[:50] + "...")
            
            # Test 2: List campaigns
            result = await client.call_tool("list_campaigns", {})
            print("✅ list_campaigns:", result[0].text[:50] + "...")
            
            # Test 3: Roll dice
            result = await client.call_tool("roll_dice", {
                "dice_notation": "1d20+5"
            })
            print("✅ roll_dice:", result[0].text[:50] + "...")
            
            # Test 4: Create character with validation
            result = await client.call_tool("create_character", {
                "name": "Test Hero",
                "character_class": "Fighter", 
                "class_level": 1,
                "race": "Human",
                "strength": 15,
                "dexterity": 14
            })
            print("✅ create_character:", result[0].text[:50] + "...")
            
            print("\n✅ All tool functionality tests passed!")
            return True
            
    except Exception as e:
        print(f"❌ Tool functionality test failed: {e}")
        return False


def print_summary(compliance_passed: bool, functionality_passed: bool):
    """Print verification summary."""
    print("\n" + "=" * 60)
    print("📊 FastMCP 2.8.0+ Compliance Verification Summary")
    print("=" * 60)
    
    status = "✅ PASSED" if compliance_passed else "❌ FAILED"
    print(f"Compliance Check: {status}")
    
    status = "✅ PASSED" if functionality_passed else "❌ FAILED" 
    print(f"Functionality Test: {status}")
    
    overall_status = compliance_passed and functionality_passed
    status = "✅ FULLY COMPLIANT" if overall_status else "❌ NEEDS FIXES"
    print(f"\nOverall Status: {status}")
    
    if overall_status:
        print("\n🎉 Your D&D MCP Server is fully FastMCP 2.8.0+ compliant!")
        print("\nNext steps:")
        print("  • Run: fastmcp dev src/gamemaster_mcp/main.py:mcp")
        print("  • Install: fastmcp install src/gamemaster_mcp/main.py:mcp -n 'D&D Campaign Manager'")
        print("  • Test: python demo.py")
    else:
        print("\n🔧 Please fix the issues above before deployment.")
    
    return overall_status


async def main():
    """Main verification function."""
    print("🐉 D&D MCP Server - FastMCP 2.8.0+ Compliance Verification")
    print("Built with modern FastMCP framework for enhanced performance and type safety")
    
    compliance_passed = await verify_fastmcp_compliance()
    functionality_passed = await test_tool_functionality()
    
    overall_success = print_summary(compliance_passed, functionality_passed)
    
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    asyncio.run(main())
