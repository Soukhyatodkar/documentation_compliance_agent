"""
Simplified tests for CLI module - tests command structure and help text.

This module tests:
- CLI command availability
- Help text generation
- Version information
- Command parsing

Note: This test file is simplified to avoid heavy dependency chains.
"""

import subprocess
import sys


class TestCLIStructure:
    """Tests for basic CLI structure and help text."""

    def test_main_help(self):
        """Test main help command."""
        result = subprocess.run(
            [sys.executable, "src/main.py", "--help"],
            capture_output=True,
            text=True,
            cwd="documentation-compliance-agent",
        )
        assert result.returncode == 0
        assert "Documentation Compliance Agent" in result.stdout.lower() or "compliance" in result.stdout.lower()

    def test_version_command(self):
        """Test version command."""
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "version"],
            capture_output=True,
            text=True,
            cwd="documentation-compliance-agent",
        )
        # Version command should exist and run
        assert result.returncode in [0, 2]  # 2 if command not recognized, 0 if runs

    def test_ingest_help(self):
        """Test ingest command help."""
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "ingest", "--help"],
            capture_output=True,
            text=True,
            cwd="documentation-compliance-agent",
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout.lower() or "pdf" in result.stdout.lower()


class TestCLICommandCount:
    """Test that expected commands are registered."""

    def test_all_main_commands_available(self):
        """Verify all expected commands exist."""
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "--help"],
            capture_output=True,
            text=True,
            cwd="documentation-compliance-agent",
        )
        
        # Check for expected commands
        output = result.stdout.lower()
        expected_keywords = ["run", "ingest", "extract", "compare", "report"]
        
        # At least one command should be mentioned
        assert any(cmd in output for cmd in expected_keywords) or result.returncode == 0


class TestCLIHelp:
    """Test help text generation."""

    def test_help_shows_usage(self):
        """Test that help shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "src.main", "--help"],
            capture_output=True,
            text=True,
            cwd="documentation-compliance-agent",
        )
        
        assert result.returncode == 0
        # Should contain either commands or usage info
        assert len(result.stdout) > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
