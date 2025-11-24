"""Compatibility launcher for the deprecated ``troostwatch.cli`` namespace."""

from troostwatch.interfaces.cli.__main__ import cli

__all__ = ["cli"]

if __name__ == "__main__":
    cli()
