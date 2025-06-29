# Roo's FastMCP Development Guidelines

1. **Log Changes**: After every significant change, append a brief, timestamped description to [`roo_actions.log`](.roo/roo_actions.log).
2. **Project Structure**: Adhere to the [`gamemaster-mcp/src/gamemaster_mcp/`](src/gamemaster_mcp/) structure for server implementation, models, and storage.
3. **FastMCP Tooling**:
    * **Imports**: Always use `from fastmcp import FastMCP` and `from pydantic import Field`, along with `typing` module imports (`Annotated`, `Optional`, `Literal`, `List`, `Dict`).
    * **Tool Definition**: Decorate all tools with `@mcp.tool`.
    * **Type Annotations**: Use `Annotated[Type, Field(description="...")]` for *all* tool parameters. FastMCP automatically generates schemas and validates parameters based on these annotations (e.g., `ge`, `le`, `min_length`, `max_length`, `pattern`).
    * **Docstrings**: The first line of a tool's docstring becomes its description for the LLM interface.
    * **Return Types**: Always specify the return type for tools, typically `str` for responses.
    * **Naming**: Use descriptive `action_noun` patterns for tool function names (e.g., `create_campaign`, `get_character`).
4. **Data Persistence**:
    * Interact with campaign data and adventure logs via the `DnDStorage` class in [`src/gamemaster_mcp/storage.py`](src/gamemaster_mcp/storage.py:27).
    * Understand the `_current_campaign` (single active campaign) and `_events` (global adventure log) in-memory objects.
    * Utilize the public methods of `DnDStorage` (e.g., `create_campaign`, `add_character`, `update_game_state`, `add_event`) for all data operations.
5. **Data Models**: Refer to the Pydantic models in [`src/gamemaster_mcp/models.py`](src/gamemaster_mcp/models.py) for data structures and validation rules when defining tool parameters or interacting with the storage layer.
6. **Development Workflow**:
    * Use `uv` for dependency management and execution (`uv venv`, `uv pip install -e .[dev]`, `uv run gamemaster-mcp`).
    * Run tests with `uv run pytest` and type checking with `uv run mypy src/`.
    * Ensure code style with `uv run ruff check .` and `uv run ruff format .`.
7. **Testing Tools**: Tools can be tested directly as regular Python functions or via the `fastmcp.Client`.
8. **Debugging**: Pay close attention to `Annotated` syntax for type annotation errors. FastMCP handles parameter validation automatically.
9. **Automated Checks and Style Enforcement**:
    * **Pre-commit Hooks**: The project uses `pre-commit` to automate checks before commits. These include:
        * `trailing-whitespace`: Removes trailing whitespace.
        * `end-of-file-fixer`: Ensures files end with a single newline.
        * `check-yaml`: Validates YAML file syntax.
        * `check-added-large-files`: Prevents committing excessively large files.
        * `check-merge-conflict`: Detects unresolved merge conflict markers.
        * `debug-statements`: Catches common Python debug statements (`pdb`, `breakpoint`).
        * `uv-lock` & `uv-export`: Manage `uv` dependency lock files.
        * `ruff`: Automatically formats and lints Python code according to `pyproject.toml` rules (line length 100, specific error codes ignored).
        * `mypy`: Performs static type checking based on `pyproject.toml` and `mypy.ini` configurations (e.g., disallowing untyped definitions, strict equality, warning on unused ignores).
    * **Markdown Linting (`.markdownlint.jsonc`)**: Markdown files are linted with specific rules:
        * Headings require 1 blank line above and 0 below (`MD022`).
        * Line length (`MD013`), multiple top-level headings (`MD025`), lists surrounded by blank lines (`MD032`), and unordered list indentation (`MD007`) are disabled.
    * **Python Formatting & Linting (`pyproject.toml` & `ruff`)**:
        * Python code adheres to a maximum line length of 100 characters.
        * Ruff linter checks for common errors, formatting issues, import order, naming conventions, and general warnings.
        * Specific rules like `E501` (line too long, handled by `ruff format`) and `F403` (`from module import *`) are ignored.
    * **Python Type Checking (`pyproject.toml` & `mypy.ini`)**:
        * Strict type checking is enforced for Python 3.12.
        * Untyped function definitions and incomplete definitions are disallowed.
        * Warnings are issued for `Any` types, unused configurations, redundant casts, unused ignores, and unreachable code.
        * Implicit optional types are disallowed.
        * Strict equality checks are enabled.
        * Missing imports are ignored for `mcp.*` and `pydantic.*` modules.
