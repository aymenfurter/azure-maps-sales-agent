"""
Unit tests for mock_api.py
"""
import pytest
from datetime import datetime
from mock_api import get_todays_clients, get_client_details, SAMPLE_CLIENTS


def test_get_todays_clients():
    """Test the get_todays_clients function returns expected data structure."""
    # Test with default count
    result = get_todays_clients()
    
    # Validate structure
    assert isinstance(result, dict)
    assert "date" in result
    assert "office" in result
    assert "clients" in result
    
    # Validate date format (YYYY-MM-DD)
    assert datetime.strptime(result["date"], "%Y-%m-%d")
    
    # Validate office data
    assert result["office"]["name"] == "Office"
    assert "address" in result["office"]
    assert "coordinates" in result["office"]
    
    # Validate clients data
    assert isinstance(result["clients"], list)
    assert 2 <= len(result["clients"]) <= len(SAMPLE_CLIENTS)
    
    # Test with specific count
    specific_count = 2
    result_specific = get_todays_clients(count=specific_count)
    assert len(result_specific["clients"]) == specific_count
    
    # Validate client properties
    for client in result["clients"]:
        assert "id" in client
        assert "name" in client
        assert "contact" in client
        assert "address" in client
        assert "coordinates" in client
        assert "priority" in client


def test_get_client_details_existing():
    """Test get_client_details with an existing client ID."""
    # Get a known client ID
    client_id = SAMPLE_CLIENTS[0]["id"]
    
    # Get client details
    result = get_client_details(client_id)
    
    # Validate structure
    assert isinstance(result, dict)
    assert not "error" in result
    
    # Validate original fields are preserved
    assert result["id"] == client_id
    assert result["name"] == SAMPLE_CLIENTS[0]["name"]
    assert result["contact"] == SAMPLE_CLIENTS[0]["contact"]
    assert result["address"] == SAMPLE_CLIENTS[0]["address"]
    assert result["coordinates"] == SAMPLE_CLIENTS[0]["coordinates"]
    assert result["priority"] == SAMPLE_CLIENTS[0]["priority"]
    
    # Validate additional fields are present
    assert "last_visit" in result
    assert "total_purchases" in result
    assert "active_contracts" in result
    assert "notes" in result
    
    # Validate last_visit format
    assert datetime.strptime(result["last_visit"], "%Y-%m-%d")
    
    # Validate numeric fields
    assert isinstance(result["total_purchases"], float)
    assert isinstance(result["active_contracts"], int)
    
    # Validate notes field is a string
    assert isinstance(result["notes"], str)


def test_get_client_details_nonexistent():
    """Test get_client_details with a non-existent client ID."""
    # Use a non-existent ID
    client_id = "NONEXISTENT_ID"
    
    # Get client details
    result = get_client_details(client_id)
    
    # Validate error response
    assert isinstance(result, dict)
    assert "error" in result
    assert client_id in result["error"]
    assert "not found" in result["error"]