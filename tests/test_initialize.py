"""
Unit tests for initialize.py
"""

import os
from unittest.mock import patch

import initilize


def test_check_azure_maps_key_not_set(capsys):
    """Test when Azure Maps API key is not set in environment."""
    with patch.dict(os.environ, {"AZURE_MAPS_KEY": ""}, clear=True):
        initilize.check_azure_maps_key()
        captured = capsys.readouterr()
        assert "WARNING: AZURE_MAPS_KEY environment variable not found" in captured.out
        assert "This application requires an Azure Maps API key" in captured.out


def test_check_azure_maps_key_set(capsys):
    """Test when Azure Maps API key is set in environment."""
    with patch.dict(os.environ, {"AZURE_MAPS_KEY": "test-key-value"}):
        initilize.check_azure_maps_key()
        captured = capsys.readouterr()
        assert "Azure Maps API key found in environment variables" in captured.out


def test_main_function(capsys):
    """Test the main function execution."""
    with patch.dict(os.environ, {"AZURE_MAPS_KEY": "test-key-value"}):
        with patch("initilize.load_dotenv") as mock_load_dotenv:
            initilize.main()

            # Check if load_dotenv was called with override=True
            mock_load_dotenv.assert_called_once_with(override=True)

            # Check output
            captured = capsys.readouterr()
            assert "Sales Day Planning Assistant - Initialization" in captured.out
            assert "Initialization completed" in captured.out
