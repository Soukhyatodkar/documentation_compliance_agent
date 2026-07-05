"""
Main CLI entry point for Documentation Compliance Agent.

This module imports and runs the CLI application defined in src.cli.commands.
It serves as the entry point for the python -m src.main command.

The CLI provides commands for:
- run: Execute the complete compliance pipeline
- ingest: Ingest PDF guidelines
- extract: Extract website components
- compare: Compare components with guidelines
- report: Generate compliance reports
- config: Display configuration
- test-connection: Test external service connections
- status: Show project statistics
- version: Display version information
"""

from src.cli.commands import app

if __name__ == "__main__":
    app()
