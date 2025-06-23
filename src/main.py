#!/usr/bin/env python3
"""
CLI entry point for the D&D MCP Server.
"""

import asyncio
from dnd_mcp_server.main import main

def cli_main():
    """Main CLI entry point."""
    asyncio.run(main())

if __name__ == "__main__":
    cli_main()
