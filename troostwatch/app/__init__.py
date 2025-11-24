"""Application orchestration layer.

Coordinates configuration, interfaces and services. Modules here forward to
existing implementations to enable incremental migration to the layered
architecture.
"""

from . import config

__all__ = ["config"]
