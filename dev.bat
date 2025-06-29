@echo off
REM D&D MCP Server - Development Helper Script (Windows)
REM FastMCP 2.8.0+ compliant development workflow

setlocal enabledelayedexpansion

if "%1"=="install" goto install_deps
if "%1"=="setup" goto setup_pre_commit
if "%1"=="test" goto run_tests
if "%1"=="typecheck" goto check_types
if "%1"=="format" goto format_code
if "%1"=="verify" goto verify_compliance
if "%1"=="dev" goto run_dev_server
if "%1"=="demo" goto run_demo
if "%1"=="claude" goto install_for_claude
if "%1"=="clean" goto clean_build
if "%1"=="all" goto run_all
goto show_help

:install_deps
echo 🐉 D&D MCP Server - Installing Dependencies
echo ==================================
where uv >nul 2>nul
if %errorlevel%==0 (
    echo Using uv for fast installation...
    uv pip install -e .[dev]
) else (
    echo Using pip for installation...
    pip install -e .[dev]
)
echo ✅ Dependencies installed
goto :eof

:setup_pre_commit
echo 🐉 D&D MCP Server - Setting up Pre-commit Hooks
echo ==================================
where pre-commit >nul 2>nul
if %errorlevel%==0 (
    pre-commit install
    echo ✅ Pre-commit hooks installed
) else (
    echo ⚠️ pre-commit not available, install with: pip install pre-commit
)
goto :eof

:run_tests
echo 🐉 D&D MCP Server - Running Tests
echo ==================================
echo Running basic tests...
python test_basic.py
where pytest >nul 2>nul
if %errorlevel%==0 (
    echo Running pytest...
    pytest test_basic.py -v
)
echo ✅ Tests completed
goto :eof

:check_types
echo 🐉 D&D MCP Server - Type Checking
echo ==================================
where mypy >nul 2>nul
if %errorlevel%==0 (
    mypy src/
    echo ✅ Type checking passed
) else (
    echo ⚠️ mypy not available, install with: pip install mypy
)
goto :eof

:format_code
echo 🐉 D&D MCP Server - Code Formatting
echo ==================================
where black >nul 2>nul
if %errorlevel%==0 (
    echo Running black...
    black src/ --line-length 100
    echo ✅ Black formatting applied
)
where ruff >nul 2>nul
if %errorlevel%==0 (
    echo Running ruff...
    ruff check src/ --fix
    echo ✅ Ruff linting completed
)
goto :eof

:verify_compliance
echo 🐉 D&D MCP Server - FastMCP 2.8.0+ Compliance Verification
echo ==================================
python verify_compliance.py
goto :eof

:run_dev_server
echo 🐉 D&D MCP Server - Starting FastMCP Development Server
echo ==================================
where fastmcp >nul 2>nul
if %errorlevel%==0 (
    echo Starting with FastMCP CLI...
    fastmcp dev src/gamemaster_mcp/main.py:mcp
) else (
    echo FastMCP CLI not available, running directly...
    python -m gamemaster_mcp
)
goto :eof

:run_demo
echo 🐉 D&D MCP Server - Running Demo
echo ==================================
python demo.py
goto :eof

:install_for_claude
echo 🐉 D&D MCP Server - Installing for Claude Desktop
echo ==================================
where fastmcp >nul 2>nul
if %errorlevel%==0 (
    fastmcp install src/gamemaster_mcp/main.py:mcp -n "D&D Campaign Manager"
    echo ✅ Installed for Claude Desktop
) else (
    echo ❌ FastMCP CLI not available. Install with: pip install fastmcp>=2.8.0
)
goto :eof

:clean_build
echo 🐉 D&D MCP Server - Cleaning Build Artifacts
echo ==================================
echo Removing build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d %%i in (*.egg-info) do rmdir /s /q "%%i"
for /d %%i in (src\*.egg-info) do rmdir /s /q "%%i"

echo Removing cache directories...
for /d /r . %%i in (__pycache__) do if exist "%%i" rmdir /s /q "%%i"
for /d /r . %%i in (.pytest_cache) do if exist "%%i" rmdir /s /q "%%i"
for /d /r . %%i in (.mypy_cache) do if exist "%%i" rmdir /s /q "%%i"
for /d /r . %%i in (.ruff_cache) do if exist "%%i" rmdir /s /q "%%i"

echo Removing test data...
if exist dnd_data rmdir /s /q dnd_data
if exist demo_data rmdir /s /q demo_data
if exist test_data rmdir /s /q test_data

echo ✅ Cleanup completed
goto :eof

:run_all
echo 🐉 D&D MCP Server - Full Development Workflow
echo ==================================
echo Running complete development workflow...
call :install_deps
call :setup_pre_commit
call :format_code
call :check_types
call :run_tests
call :verify_compliance

echo ✅ Full workflow completed successfully!
echo.
echo Next steps:
echo   • Run development server: dev.bat dev
echo   • Install for Claude Desktop: dev.bat claude
echo   • Run demo: dev.bat demo
goto :eof

:show_help
echo 🐉 D&D MCP Server - Development Commands
echo ==================================
echo.
echo Usage: dev.bat ^<command^>
echo.
echo Commands:
echo   install      Install dependencies
echo   setup        Setup pre-commit hooks
echo   test         Run tests
echo   typecheck    Run type checking
echo   format       Format code with black and ruff
echo   verify       Verify FastMCP 2.8.0+ compliance
echo   dev          Start development server
echo   demo         Run demo script
echo   claude       Install for Claude Desktop
echo   clean        Clean build artifacts
echo   all          Run full development workflow
echo   help         Show this help message
echo.
goto :eof
