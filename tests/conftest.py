"""
Configuration and fixtures for pytest.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


def pytest_configure(config):
    """Configure pytest to skip browser tests if browsers are not installed."""
    # Register a custom marker for UI tests
    config.addinivalue_line("markers", "ui: mark test as a UI test that requires Playwright browsers")


def pytest_collection_modifyitems(config, items):
    """
    Skip UI tests if Playwright browsers are not installed.
    This allows CI to continue even if browser downloads fail.
    """
    skip_ui = pytest.mark.skip(reason="Playwright browsers not installed")

    # Check if browsers are available by checking known paths
    browsers_installed = False
    potential_paths = [
        Path.home() / ".cache" / "ms-playwright",
        Path("/ms-playwright"),
        Path(sys.prefix) / "ms-playwright",
    ]

    for path in potential_paths:
        if path.exists() and any(path.glob("**/chrome*")):
            browsers_installed = True
            break

    if not browsers_installed:
        for item in items:
            if "ui" in item.keywords:
                item.add_marker(skip_ui)


@pytest.fixture
def azure_maps_key():
    """Fixture to provide a mock Azure Maps API key."""
    return "mock_azure_maps_key_for_testing"


@pytest.fixture
def mock_env_azure_maps_key():
    """Fixture to mock the AZURE_MAPS_KEY environment variable."""
    with patch.dict(os.environ, {"AZURE_MAPS_KEY": "mock_azure_maps_key_for_testing"}):
        yield
