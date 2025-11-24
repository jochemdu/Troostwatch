"""Interface layer for Troostwatch.

Packages under ``troostwatch.interfaces`` expose boundary adapters such as CLI
commands. They currently forward to the legacy modules while imports migrate.
"""

from . import cli

__all__ = ["cli"]
