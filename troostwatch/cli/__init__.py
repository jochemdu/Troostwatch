"""Legacy CLI namespace.

This package is kept as a thin compatibility layer that forwards imports to
:mod:`troostwatch.interfaces.cli`. Existing consumers should migrate to the
``troostwatch.interfaces.cli`` namespace; the legacy path will be removed after
the deprecation period.
"""

from __future__ import annotations

import warnings

from troostwatch.interfaces.cli.__main__ import cli
from troostwatch.interfaces.cli.add_lot import add_lot
from troostwatch.interfaces.cli.bid import bid
from troostwatch.interfaces.cli.buyer import buyer
from troostwatch.interfaces.cli.debug import debug
from troostwatch.interfaces.cli.menu import menu
from troostwatch.interfaces.cli.positions import positions
from troostwatch.interfaces.cli.report import report
from troostwatch.interfaces.cli.sync import sync
from troostwatch.interfaces.cli.sync_multi import sync_multi
from troostwatch.interfaces.cli.view import view

warnings.warn(
    "`troostwatch.cli` is deprecated; import CLI commands from "
    "`troostwatch.interfaces.cli` instead.",
    DeprecationWarning,
    stacklevel=2,
)

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
