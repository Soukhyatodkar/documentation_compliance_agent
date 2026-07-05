"""
CLI module for Documentation Compliance Agent.

This module provides the command-line interface for the compliance checking system.

Classes:
    None (commands defined in commands.py)

Functions:
    get_app() - Returns the Typer app instance

Usage:
    from src.cli import commands
    commands.app()
"""

from .commands import app

__all__ = ["app"]
