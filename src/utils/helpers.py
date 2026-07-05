"""
Helper utilities for the application.

Provides general-purpose utility functions used across modules.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import hashlib


class JSONHelper:
    """JSON utility functions."""

    @staticmethod
    def save(data: Any, file_path: str, pretty: bool = True) -> None:
        """
        Save data to JSON file.

        Args:
            data: Data to save
            file_path: Path to save to
            pretty: Pretty print JSON

        Raises:
            IOError: If save fails
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w") as f:
                if pretty:
                    json.dump(data, f, indent=2, default=str)
                else:
                    json.dump(data, f, default=str)
        except Exception as e:
            raise IOError(f"Failed to save JSON to {file_path}: {str(e)}") from e

    @staticmethod
    def load(file_path: str) -> Any:
        """
        Load JSON from file.

        Args:
            file_path: Path to load from

        Returns:
            Loaded data

        Raises:
            IOError: If load fails
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"Failed to load JSON from {file_path}: {str(e)}") from e

    @staticmethod
    def dumps(data: Any, pretty: bool = True) -> str:
        """
        Convert data to JSON string.

        Args:
            data: Data to convert
            pretty: Pretty print

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)


class PathHelper:
    """Path utility functions."""

    @staticmethod
    def ensure_dir(path: str) -> Path:
        """
        Ensure directory exists (create if not).

        Args:
            path: Directory path

        Returns:
            Path object
        """
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def ensure_parent_dir(file_path: str) -> Path:
        """
        Ensure parent directory exists.

        Args:
            file_path: File path

        Returns:
            Parent directory Path
        """
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.parent

    @staticmethod
    def get_relative_path(file_path: str, base_path: str = ".") -> str:
        """
        Get relative path from base.

        Args:
            file_path: File path
            base_path: Base path

        Returns:
            Relative path as string
        """
        file_p = Path(file_path)
        base_p = Path(base_path)
        try:
            return str(file_p.relative_to(base_p))
        except ValueError:
            return str(file_p)

    @staticmethod
    def get_absolute_path(file_path: str) -> str:
        """
        Get absolute path.

        Args:
            file_path: File path

        Returns:
            Absolute path as string
        """
        return str(Path(file_path).absolute())


class TimeHelper:
    """Time utility functions."""

    @staticmethod
    def now() -> datetime:
        """Get current datetime."""
        return datetime.now()

    @staticmethod
    def now_iso() -> str:
        """Get current time in ISO format."""
        return datetime.now().isoformat()

    @staticmethod
    def now_timestamp() -> str:
        """Get current time as timestamp string."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in seconds to human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "1h 23m 45s")
        """
        if seconds < 1:
            return f"{seconds:.2f}s"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs:.1f}s")

        return " ".join(parts)

    @staticmethod
    def add_days(days: int) -> datetime:
        """Add days to current time."""
        return datetime.now() + timedelta(days=days)

    @staticmethod
    def add_hours(hours: int) -> datetime:
        """Add hours to current time."""
        return datetime.now() + timedelta(hours=hours)


class StringHelper:
    """String utility functions."""

    @staticmethod
    def truncate(text: str, length: int, suffix: str = "...") -> str:
        """
        Truncate string to length.

        Args:
            text: Text to truncate
            length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if len(text) <= length:
            return text
        return text[: length - len(suffix)] + suffix

    @staticmethod
    def remove_special_chars(text: str, keep_chars: str = "") -> str:
        """
        Remove special characters from string.

        Args:
            text: Text to clean
            keep_chars: Characters to keep (in addition to alphanumeric)

        Returns:
            Cleaned text
        """
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" + keep_chars
        return "".join(c for c in text if c in allowed)

    @staticmethod
    def slugify(text: str) -> str:
        """
        Convert text to slug format.

        Args:
            text: Text to slugify

        Returns:
            Slug (lowercase, hyphens, alphanumeric)
        """
        import re

        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-")

    @staticmethod
    def hash_string(text: str, algorithm: str = "sha256") -> str:
        """
        Hash string.

        Args:
            text: Text to hash
            algorithm: Hash algorithm (md5, sha1, sha256, sha512)

        Returns:
            Hex digest
        """
        h = hashlib.new(algorithm)
        h.update(text.encode())
        return h.hexdigest()


class ListHelper:
    """List utility functions."""

    @staticmethod
    def flatten(nested_list: List) -> List:
        """
        Flatten nested list.

        Args:
            nested_list: Nested list

        Returns:
            Flattened list
        """
        result = []
        for item in nested_list:
            if isinstance(item, list):
                result.extend(ListHelper.flatten(item))
            else:
                result.append(item)
        return result

    @staticmethod
    def deduplicate(items: List) -> List:
        """
        Remove duplicates from list while preserving order.

        Args:
            items: List of items

        Returns:
            List without duplicates
        """
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def chunk(items: List, size: int) -> List[List]:
        """
        Split list into chunks.

        Args:
            items: List to chunk
            size: Chunk size

        Returns:
            List of chunks
        """
        return [items[i : i + size] for i in range(0, len(items), size)]


class DictHelper:
    """Dictionary utility functions."""

    @staticmethod
    def deep_merge(base: Dict, updates: Dict) -> Dict:
        """
        Deep merge updates into base dictionary.

        Args:
            base: Base dictionary
            updates: Updates to merge

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DictHelper.deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def get_nested(data: Dict, key_path: str, default: Any = None) -> Any:
        """
        Get nested dictionary value using dot notation.

        Args:
            data: Dictionary to query
            key_path: Path (e.g., "a.b.c")
            default: Default value

        Returns:
            Value at path or default

        Example:
            DictHelper.get_nested({"a": {"b": {"c": 1}}}, "a.b.c")  # Returns 1
        """
        keys = key_path.split(".")
        value = data

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    @staticmethod
    def set_nested(data: Dict, key_path: str, value: Any) -> Dict:
        """
        Set nested dictionary value using dot notation.

        Args:
            data: Dictionary to update
            key_path: Path (e.g., "a.b.c")
            value: Value to set

        Returns:
            Updated dictionary

        Example:
            DictHelper.set_nested({}, "a.b.c", 1)  # Returns {"a": {"b": {"c": 1}}}
        """
        keys = key_path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
        return data

    @staticmethod
    def filter_keys(data: Dict, keys: List[str]) -> Dict:
        """
        Filter dictionary to only include specified keys.

        Args:
            data: Dictionary to filter
            keys: Keys to keep

        Returns:
            Filtered dictionary
        """
        return {k: v for k, v in data.items() if k in keys}

    @staticmethod
    def exclude_keys(data: Dict, keys: List[str]) -> Dict:
        """
        Filter dictionary to exclude specified keys.

        Args:
            data: Dictionary to filter
            keys: Keys to exclude

        Returns:
            Filtered dictionary
        """
        return {k: v for k, v in data.items() if k not in keys}
