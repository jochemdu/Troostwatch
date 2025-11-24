"""CLI interface facades for Troostwatch.

This package exposes the existing Click commands under the
``troostwatch.interfaces.cli`` namespace to support phased import updates.
"""

from .__main__ import cli
from .add_lot import add_lot
from .auth import auth
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
    "auth",
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
