"""Entry point facade for the CLI interface layer."""

from troostwatch.cli.__main__ import cli

__all__ = ["cli"]

if __name__ == "__main__":
    cli()
