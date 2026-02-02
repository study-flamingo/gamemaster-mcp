"""
Rulebook data sources.

This subpackage provides implementations for different rulebook sources:
- SRD: Official D&D 5e System Reference Document via 5e-srd-api
- Custom: Local JSON/YAML files for homebrew content
- Open5e: Extended OGL content (future)
"""

from .base import RulebookSourceBase, SearchResult, ContentCounts
from .custom import CustomSource, CustomSourceError
from .srd import SRDSource, SRDSourceError

__all__ = [
    # Base
    "RulebookSourceBase",
    "SearchResult",
    "ContentCounts",
    # SRD source
    "SRDSource",
    "SRDSourceError",
    # Custom source
    "CustomSource",
    "CustomSourceError",
]
