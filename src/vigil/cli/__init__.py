"""Command-line entry point for Vigil."""

from vigil.cli.commands import app
from vigil.cli.menu import MenuConfig

__all__ = ["MenuConfig", "app"]
