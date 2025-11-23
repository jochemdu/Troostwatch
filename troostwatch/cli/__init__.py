"""CLI entry points for Troostwatch.

This module aggregates the subcommands for the Troostwatch command line interface.
"""

# Re-export command functions so that ``python -m troostwatch.cli`` can
# discover subcommands via setuptools entry points. Import buyer to
# register the ``buyer`` group when this package is imported.

from .buyer import buyer  # noqa: F401

__all__ = ["buyer"]