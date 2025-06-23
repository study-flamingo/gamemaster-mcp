#!/usr/bin/env python3
"""
Main entry point for the D&D MCP Server.
"""

import asyncio
from .main import main

if __name__ == "__main__":
    asyncio.run(main())
