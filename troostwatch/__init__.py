"""
Troostwatch package initializer.

This package provides tools for scraping, analyzing and tracking auctions on the Troostwijk platform.

The package exposes a ``__version__`` attribute indicating the installed
version of Troostwatch. The version is read from pyproject.toml via
importlib.metadata – this is the single source of truth.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("troostwatch")
except PackageNotFoundError:
    # Package is not installed (running from source without pip install -e .)
    __version__ = "0.0.0.dev"

__all__: list[str] = ["__version__"]
