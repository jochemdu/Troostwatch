"""CLI interface facades for Troostwatch.

This package is the canonical home for all Click commands. Use the
``troostwatch.interfaces.cli`` namespace for imports and module execution; the
legacy ``troostwatch.cli`` package now only proxies to these implementations
and emits a deprecation warning on import.
"""

from .__main__ import cli
from .add_lot import add_lot
from .bid import bid
from .buyer import buyer
from .debug import debug
from .menu import menu
from .positions import positions
from .report import report
from .sync import sync
from .sync_multi import sync_multi
from .view import view

__all__ = [
    "add_lot",
    "bid",
    "buyer",
    "cli",
    "debug",
    "menu",
    "positions",
    "report",
    "sync",
    "sync_multi",
    "view",
]
