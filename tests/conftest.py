"""
Configuration and fixtures for pytest.
"""
import os
import pytest
from unittest.mock import patch


@pytest.fixture
def azure_maps_key():
    """Fixture to provide a mock Azure Maps API key."""
    return "mock_azure_maps_key_for_testing"


@pytest.fixture
def mock_env_azure_maps_key():
    """Fixture to mock the AZURE_MAPS_KEY environment variable."""
    with patch.dict(os.environ, {"AZURE_MAPS_KEY": "mock_azure_maps_key_for_testing"}):
        yield