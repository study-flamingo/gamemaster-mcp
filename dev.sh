#!/usr/bin/env bash
# 
# D&D MCP Server - Development Helper Script
# FastMCP 2.8.0+ compliant development workflow
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}🐉 D&D MCP Server - $1${NC}"
    echo "=================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Functions
install_deps() {
    print_header "Installing Dependencies"
    
    if command -v uv &> /dev/null; then
        echo "Using uv for fast installation..."
        uv pip install -e .[dev]
    else
        echo "Using pip for installation..."
        pip install -e .[dev]
    fi
    
    print_success "Dependencies installed"
}

setup_pre_commit() {
    print_header "Setting up Pre-commit Hooks"
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "pre-commit not available, install with: pip install pre-commit"
    fi
}

run_tests() {
    print_header "Running Tests"
    
    echo "Running basic tests..."
    python test_basic.py
    
    if command -v pytest &> /dev/null; then
        echo "Running pytest..."
        pytest test_basic.py -v
    fi
    
    print_success "Tests completed"
}

check_types() {
    print_header "Type Checking"
    
    if command -v mypy &> /dev/null; then
        mypy src/
        print_success "Type checking passed"
    else
        print_warning "mypy not available, install with: pip install mypy"
    fi
}

format_code() {
    print_header "Code Formatting"
    
    if command -v black &> /dev/null; then
        echo "Running black..."
        black src/ --line-length 100
        print_success "Black formatting applied"
    fi
    
    if command -v ruff &> /dev/null; then
        echo "Running ruff..."
        ruff check src/ --fix
        print_success "Ruff linting completed"
    fi
}

verify_compliance() {
    print_header "FastMCP 2.8.0+ Compliance Verification"
    python verify_compliance.py
}

run_dev_server() {
    print_header "Starting FastMCP Development Server"
    
    if command -v fastmcp &> /dev/null; then
        echo "Starting with FastMCP CLI..."
        fastmcp dev src/gamemaster_mcp/main.py:mcp
    else
        echo "FastMCP CLI not available, running directly..."
        python -m gamemaster_mcp
    fi
}

run_demo() {
    print_header "Running Demo"
    python demo.py
}

install_for_claude() {
    print_header "Installing for Claude Desktop"
    
    if command -v fastmcp &> /dev/null; then
        fastmcp install src/gamemaster_mcp/main.py:mcp -n "D&D Campaign Manager"
        print_success "Installed for Claude Desktop"
    else
        print_error "FastMCP CLI not available. Install with: pip install fastmcp>=2.8.0"
    fi
}

clean_build() {
    print_header "Cleaning Build Artifacts"
    
    echo "Removing build artifacts..."
    rm -rf build/ dist/ *.egg-info/
    rm -rf src/*.egg-info/
    
    echo "Removing cache directories..."
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
    
    echo "Removing test data..."
    rm -rf dnd_data/ demo_data/ test_data/
    
    print_success "Cleanup completed"
}

show_help() {
    print_header "Development Commands"
    echo ""
    echo "Usage: ./dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  install      Install dependencies"
    echo "  setup        Setup pre-commit hooks"
    echo "  test         Run tests"
    echo "  typecheck    Run type checking"
    echo "  format       Format code with black and ruff"
    echo "  verify       Verify FastMCP 2.8.0+ compliance"
    echo "  dev          Start development server"
    echo "  demo         Run demo script"
    echo "  claude       Install for Claude Desktop"
    echo "  clean        Clean build artifacts"
    echo "  all          Run full development workflow"
    echo "  help         Show this help message"
    echo ""
}

run_all() {
    print_header "Full Development Workflow"
    
    echo "Running complete development workflow..."
    install_deps
    setup_pre_commit
    format_code
    check_types
    run_tests
    verify_compliance
    
    print_success "Full workflow completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  • Run development server: ./dev.sh dev"
    echo "  • Install for Claude Desktop: ./dev.sh claude"
    echo "  • Run demo: ./dev.sh demo"
}

# Main script logic
case "${1:-help}" in
    install)
        install_deps
        ;;
    setup)
        setup_pre_commit
        ;;
    test)
        run_tests
        ;;
    typecheck)
        check_types
        ;;
    format)
        format_code
        ;;
    verify)
        verify_compliance
        ;;
    dev)
        run_dev_server
        ;;
    demo)
        run_demo
        ;;
    claude)
        install_for_claude
        ;;
    clean)
        clean_build
        ;;
    all)
        run_all
        ;;
    help|*)
        show_help
        ;;
esac
