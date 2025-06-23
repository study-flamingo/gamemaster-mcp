"""
D&D MCP Server - A comprehensive campaign management tool for D&D built with FastMCP 2.8.0+.
"""

from .main import mcp
from .models import *
from .storage import DnDStorage

__version__ = "1.0.0"
__all__ = ["mcp", "DnDStorage"]
