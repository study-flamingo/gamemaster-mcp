# Table of Contents
- [Table of Contents](#table-of-contents)
- [D\&D MCP Server - Development Guide (FastMCP 2.8.0+)](#dd-mcp-server---development-guide-fastmcp-280)
  - [📁 Project Structure](#-project-structure)
  - [🚀 FastMCP 2.8.0+ Architecture](#-fastmcp-280-architecture)
    - [**Major Changes from Raw MCP SDK**](#major-changes-from-raw-mcp-sdk)
      - [**1. Import Statement**](#1-import-statement)
      - [**2. Server Initialization**](#2-server-initialization)
      - [**3. Tool Definition**](#3-tool-definition)
      - [**4. Type Annotations \& Validation**](#4-type-annotations--validation)
      - [**5. Server Execution**](#5-server-execution)
  - [🏗️ FastMCP Tool Architecture](#️-fastmcp-tool-architecture)
    - [**Tool Categories (25+ tools)**](#tool-categories-25-tools)
    - [**FastMCP Tool Implementation Pattern**](#fastmcp-tool-implementation-pattern)
    - [**Advanced Parameter Types**](#advanced-parameter-types)
  - [💾 Storage Layer (Unchanged)](#-storage-layer-unchanged)
  - [🎯 Development Workflows](#-development-workflows)
    - [**Adding a New Tool with FastMCP 2.8.0+**](#adding-a-new-tool-with-fastmcp-280)
    - [**Extending Data Models**](#extending-data-models)
    - [**Testing with FastMCP CLI**](#testing-with-fastmcp-cli)
  - [🧪 Testing \& Validation](#-testing--validation)
    - [**FastMCP Development Workflow**](#fastmcp-development-workflow)
    - [**Tool Testing**](#tool-testing)
  - [🔍 Debugging \& Troubleshooting](#-debugging--troubleshooting)
    - [**FastMCP-Specific Issues**](#fastmcp-specific-issues)
      - [**Type Annotation Errors**](#type-annotation-errors)
      - [**Parameter Validation Issues**](#parameter-validation-issues)
      - [**Import Issues**](#import-issues)
    - [**Development Tools**](#development-tools)
  - [🚀 Deployment](#-deployment)
    - [**Claude Desktop Integration**](#claude-desktop-integration)
    - [**FastMCP CLI Installation**](#fastmcp-cli-installation)
  - [📝 Code Style \& Standards (Updated)](#-code-style--standards-updated)
    - [**FastMCP-Specific Conventions**](#fastmcp-specific-conventions)
    - [**Parameter Guidelines**](#parameter-guidelines)
  - [💡 Performance Considerations](#-performance-considerations)
    - [**FastMCP Advantages**](#fastmcp-advantages)
    - [**Migration Benefits**](#migration-benefits)
  - [🔧 Migration Checklist](#-migration-checklist)
    - [**From Raw MCP SDK to FastMCP 2.8.0+**](#from-raw-mcp-sdk-to-fastmcp-280)


# D&D MCP Server - Development Guide (FastMCP 2.8.0+)

## 📁 Project Structure

```
dnd-mcp/
├── src/
│   ├── gamemaster_mcp/           # Renamed for FastMCP compliance
│   │   ├── __init__.py          # Package initialization
│   │   ├── __main__.py          # Module entry point
│   │   ├── main.py              # FastMCP 2.8.0+ server implementation
│   │   ├── models.py            # Pydantic data models
│   │   └── storage.py           # Data persistence layer
│   └── main.py                  # CLI entry point
├── demo.py                      # Example usage script
├── requirements.txt             # Runtime dependencies
├── pyproject.toml              # Project configuration (FastMCP compliant)
├── mypy.ini                    # Type checking configuration
├── .gitignore                  # Git ignore rules
└── README.md                   # User documentation
```

## 🚀 FastMCP 2.8.0+ Architecture

### **Major Changes from Raw MCP SDK**

#### **1. Import Statement**
```python
# Old (Raw MCP SDK)
from mcp.server import Server
from mcp.server.stdio import stdio_server

# New (FastMCP 2.8.0+)
from fastmcp import FastMCP
```

#### **2. Server Initialization**
```python
# Old
app = Server("dnd-mcp-server")

# New
mcp = FastMCP(
    name="D&D Campaign Manager",
    dependencies=["pydantic>=2.0.0", "typing-extensions>=4.0.0"]
)
```

#### **3. Tool Definition**
```python
# Old (Manual tool registration)
@app.list_tools()
async def handle_list_tools() -> List[Tool]:
    return [Tool(name="create_campaign", ...)]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "create_campaign":
        # Manual implementation

# New (Decorator-based)
@mcp.tool
def create_campaign(
    name: Annotated[str, Field(description="Campaign name")],
    description: Annotated[str, Field(description="Campaign description")]
) -> str:
    """Create a new D&D campaign."""
    # Implementation
```

#### **4. Type Annotations & Validation**
```python
# FastMCP 2.8.0+ automatically generates schemas from type hints
@mcp.tool
def create_character(
    name: Annotated[str, Field(description="Character name")],
    class_level: Annotated[int, Field(description="Class level", ge=1, le=20)],
    alignment: Annotated[Optional[str], Field(description="Character alignment")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
) -> str:
    """Create a new player character with automatic validation."""
```

#### **5. Server Execution**
```python
# Old
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, ...)

# New
def main() -> None:
    """Main entry point for the D&D MCP Server."""
    mcp.run()
```

## 🏗️ FastMCP Tool Architecture

### **Tool Categories (25+ tools)**

1. **Campaign Tools** (4) - Automatic schema generation
2. **Character Tools** (5) - Rich parameter validation
3. **NPC Tools** (3) - Type-safe implementations
4. **Location Tools** (3) - Literal type constraints
5. **Quest Tools** (3) - Optional parameter handling
6. **Game State Tools** (2) - Complex object updates
7. **Combat Tools** (3) - List parameter processing
8. **Session Tools** (2) - Nested data structures
9. **Event Tools** (2) - Search and filtering
10. **Utility Tools** (2) - Mathematical calculations

### **FastMCP Tool Implementation Pattern**

```python
@mcp.tool
def tool_name(
    # Required parameters (no default value)
    required_param: Annotated[str, Field(description="Required parameter")],
    
    # Optional parameters (with default values)
    optional_param: Annotated[Optional[str], Field(description="Optional parameter")] = None,
    
    # Validated parameters (with constraints)
    validated_param: Annotated[int, Field(description="Validated param", ge=1, le=100)] = 10,
    
    # Literal constraints (enum-like)
    constrained_param: Annotated[Literal["option1", "option2"], Field(description="Constrained choices")] = "option1",
    
    # Complex types (lists, dicts)
    complex_param: Annotated[List[str], Field(description="List of strings")] = None,
) -> str:
    """
    Tool description that appears in the LLM interface.
    
    FastMCP automatically:
    - Generates JSON schema from type annotations
    - Validates parameters according to Pydantic Field constraints
    - Routes requests to this function
    - Handles errors and type conversion
    """
    # Implementation logic
    if complex_param is None:
        complex_param = []
    
    # Process parameters
    result = process_logic(required_param, optional_param, validated_param)
    
    # Return formatted response
    return f"Processed {required_param} with result: {result}"
```

### **Advanced Parameter Types**

```python
# Annotated Field Examples
@mcp.tool
def advanced_example(
    # String with pattern validation
    user_id: Annotated[str, Field(
        pattern=r"^[A-Z]{2}\d{4}$",
        description="User ID in format XX0000"
    )],
    
    # Number with range constraints
    level: Annotated[int, Field(
        ge=1, le=20,
        description="Character level between 1 and 20"
    )],
    
    # String with length constraints
    description: Annotated[str, Field(
        min_length=10, max_length=500,
        description="Description between 10-500 characters"
    )],
    
    # List with item constraints
    tags: Annotated[List[str], Field(
        description="List of tags",
        max_items=10
    )] = None,
    
    # Literal type for strict choices
    status: Annotated[Literal["active", "completed", "failed"], Field(
        description="Quest status"
    )] = "active",
) -> str:
    """Example of advanced parameter validation."""
```

## 💾 Storage Layer (Unchanged)

The storage layer remains largely unchanged, as FastMCP focuses on the tool interface:

```python
class DnDStorage:
    """Handles storage and retrieval of D&D campaign data."""
    
    # CRUD operations remain the same
    def create_campaign(self, name: str, description: str, ...) -> Campaign:
        # Implementation unchanged
    
    def get_current_campaign(self) -> Optional[Campaign]:
        # Implementation unchanged
    
    # All existing methods work with FastMCP
```

## 🎯 Development Workflows

### **Adding a New Tool with FastMCP 2.8.0+**

1. **Define Tool with Type Annotations**:
```python
@mcp.tool
def new_spell_tool(
    spell_name: Annotated[str, Field(description="Name of the spell")],
    spell_level: Annotated[int, Field(description="Spell level", ge=0, le=9)],
    school: Annotated[Literal["evocation", "enchantment", "necromancy"], Field(description="School of magic")],
    character_name: Annotated[Optional[str], Field(description="Character to add spell to")] = None,
) -> str:
    """Add a spell to the campaign or character spellbook."""
    # Implementation
    if character_name:
        character = storage.get_character(character_name)
        if not character:
            return f"Character '{character_name}' not found."
        # Add spell to character
    else:
        # Add to campaign spell library
    
    return f"Added spell '{spell_name}' (Level {spell_level} {school})"
```

2. **FastMCP Automatically Handles**:
   - ✅ JSON schema generation
   - ✅ Parameter validation
   - ✅ Type conversion
   - ✅ Error handling
   - ✅ Tool registration

### **Extending Data Models**

Models remain Pydantic-based and work seamlessly:

```python
class Spell(BaseModel):
    """Enhanced spell model."""
    name: str
    level: int = Field(ge=0, le=9)
    school: Literal["evocation", "enchantment", "necromancy", ...]
    description: str
    components: List[str] = Field(default_factory=list)
    
    # FastMCP automatically understands Pydantic models
```

### **Testing with FastMCP CLI**

```bash
# Development with inspector
fastmcp dev src/gamemaster_mcp/main.py:mcp

# Install for Claude Desktop
fastmcp install src/gamemaster_mcp/main.py:mcp -n "D&D Campaign Manager"

# Run demo
python demo.py
```

## 🧪 Testing & Validation

### **FastMCP Development Workflow**

```bash
# Install in development mode
pip install -e .[dev]

# Run development server with inspector
fastmcp dev src/gamemaster_mcp/main.py:mcp

# Type checking (unchanged)
mypy src/

# Code formatting (unchanged)
black src/
ruff check src/

# Run tests (unchanged)
pytest
```

### **Tool Testing**

FastMCP provides better testing capabilities:

```python
# Test tools directly
import asyncio
from gamemaster_mcp.main import mcp

async def test_create_campaign():
    # Tools can be tested as regular Python functions
    result = create_campaign(
        name="Test Campaign",
        description="A test campaign"
    )
    assert "Created campaign 'Test Campaign'" in result

# Or test via MCP client
from fastmcp import Client

async def test_via_client():
    async with Client(mcp) as client:
        result = await client.call_tool("create_campaign", {
            "name": "Test Campaign",
            "description": "A test campaign"
        })
        assert result
```

## 🔍 Debugging & Troubleshooting

### **FastMCP-Specific Issues**

#### **Type Annotation Errors**
```python
# ❌ Wrong: Missing Annotated wrapper
def bad_tool(param: str = Field(description="Bad")) -> str:
    pass

# ✅ Correct: Proper Annotated syntax
def good_tool(
    param: Annotated[str, Field(description="Good")]
) -> str:
    pass
```

#### **Parameter Validation Issues**
```python
# FastMCP validates parameters automatically
@mcp.tool
def validate_example(
    level: Annotated[int, Field(ge=1, le=20)]  # Will reject values outside 1-20
) -> str:
    # No need for manual validation
    return f"Level {level} is valid!"
```

#### **Import Issues**
```python
# ✅ Correct FastMCP 2.8.0+ imports
from fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Optional, Literal, List, Dict
```

### **Development Tools**

```bash
# Check FastMCP version
fastmcp version

# Validate tool schemas
fastmcp dev src/gamemaster_mcp/main.py:mcp --validate

# Debug with inspector
fastmcp dev src/gamemaster_mcp/main.py:mcp --debug
```

## 🚀 Deployment

### **Claude Desktop Integration**

```json
{
  "mcpServers": {
    "dnd-campaign-manager": {
      "command": "fastmcp",
      "args": ["run", "/path/to/gamemaster_mcp/main.py:mcp"]
    }
  }
}
```

### **FastMCP CLI Installation**

```bash
# Install server for Claude Desktop
fastmcp install src/gamemaster_mcp/main.py:mcp -n "D&D Campaign Manager"

# With dependencies
fastmcp install src/gamemaster_mcp/main.py:mcp -n "D&D Campaign Manager" \
  --with "pydantic>=2.0.0" --with "typing-extensions>=4.0.0"
```

## 📝 Code Style & Standards (Updated)

### **FastMCP-Specific Conventions**
- **Tool Functions**: Use descriptive names with action_noun pattern (`create_campaign`, `get_character`)
- **Type Annotations**: Always use `Annotated[Type, Field(...)]` for parameters
- **Docstrings**: First line becomes tool description for LLM
- **Parameter Descriptions**: Use clear, LLM-friendly descriptions in Field()
- **Return Types**: Always specify return type (usually `str` for tool responses)

### **Parameter Guidelines**
```python
# ✅ Good: Clear, descriptive, validated
@mcp.tool  
def good_tool(
    character_name: Annotated[str, Field(description="Name of the character to update")],
    new_level: Annotated[int, Field(description="New character level", ge=1, le=20)],
    notes: Annotated[Optional[str], Field(description="Additional notes")] = None,
) -> str:
    """Update a character's level with optional notes."""

# ❌ Bad: Unclear, unvalidated
@mcp.tool
def bad_tool(name: str, level: int, notes: str = "") -> str:
    """Updates character."""
```

## 💡 Performance Considerations

### **FastMCP Advantages**
- **Faster Development** - Automatic schema generation
- **Better Type Safety** - Compile-time error detection
- **Reduced Boilerplate** - No manual tool registration
- **Enhanced DX** - Built-in development tools

### **Migration Benefits**
1. **Reduced Code** - ~70% less boilerplate code
2. **Better Validation** - Automatic parameter validation
3. **Improved Maintainability** - Type-safe, declarative approach
4. **Enhanced Testing** - Tools can be tested as regular functions
5. **Modern Standards** - Compliance with latest MCP best practices

## 🔧 Migration Checklist

### **From Raw MCP SDK to FastMCP 2.8.0+**

- [x] ✅ Update imports: `from fastmcp import FastMCP`
- [x] ✅ Replace `Server` with `FastMCP` initialization
- [x] ✅ Convert `@app.list_tools()` to `@mcp.tool` decorators
- [x] ✅ Replace manual tool handlers with type-annotated functions
- [x] ✅ Add Pydantic Field descriptions for all parameters
- [x] ✅ Update entry points to use `mcp.run()`
- [x] ✅ Add FastMCP CLI support in pyproject.toml
- [x] ✅ Update dependencies to `fastmcp>=2.8.0`
- [x] ✅ Test with FastMCP development server
- [x] ✅ Validate tool schemas and parameter types

---

This guide provides the foundation for developing with FastMCP 2.8.0+, emphasizing the modern, type-safe, and streamlined approach to MCP server development.
