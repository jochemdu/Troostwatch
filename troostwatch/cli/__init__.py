"""CLI entry points for Troostwatch.

This module aggregates the subcommands for the Troostwatch command line interface.
"""

# Re-export command functions so that ``python -m troostwatch.cli`` can
# discover subcommands via setuptools entry points. Import buyer to
# register the ``buyer`` group when this package is imported.

# Import CLI subcommands so that `python -m troostwatch.cli` can
# discover them via setuptools entry points. Each imported name is
# added to __all__ to make it discoverable by Click.

from .buyer import buyer  # noqa: F401
from .sync import sync  # noqa: F401
from .sync_multi import sync_multi  # noqa: F401
from .positions import positions  # noqa: F401
from .report import report  # noqa: F401
from .debug import debug  # noqa: F401

__all__ = ["buyer", "sync", "sync_multi", "positions", "report", "debug"]