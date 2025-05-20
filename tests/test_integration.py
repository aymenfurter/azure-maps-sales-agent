"""
Integration tests for sales_functions.py that run against real Azure Maps API when secrets are available.
"""

import json
import os

import pytest

import sales_functions
from mock_api import SAMPLE_CLIENTS


@pytest.fixture
def has_azure_maps_key():
    """Check if a real Azure Maps API key is available."""
    api_key = os.environ.get("AZURE_MAPS_KEY")
    # Skip if API key is not set or is a test value
    if not api_key or api_key == "mock_azure_maps_key_for_testing":
        pytest.skip("Skipping integration test - No real Azure Maps API key available")
    return api_key


@pytest.mark.integration
def test_real_plan_optimal_route(has_azure_maps_key):
    """Test plan_optimal_route using the real Azure Maps API."""
    # Use the API key to avoid 'not accessed' warning
    assert has_azure_maps_key is not None
    # Reset global state
    sales_functions.current_route = None
    sales_functions.current_client_list = SAMPLE_CLIENTS[:2]  # Use 2 sample clients to avoid too many requests
    sales_functions.current_visit_index = -1

    # Call the function to test with real API
    result = sales_functions.plan_optimal_route()
    result_data = json.loads(result)

    # Validate successful response
    assert "error" not in result_data
    assert "routes" in result_data
    assert len(result_data["routes"]) > 0

    # Check route details
    first_route = result_data["routes"][0]
    assert "summary" in first_route
    assert "legs" in first_route
    assert "lengthInMeters" in first_route["summary"]
    assert first_route["summary"]["lengthInMeters"] > 0


@pytest.mark.integration
def test_real_generate_location_map_with_query(has_azure_maps_key):
    """Test generate_location_map with query using the real Azure Maps API."""
    # Use the API key to avoid 'not accessed' warning
    assert has_azure_maps_key is not None
    # Call function with a real location query
    result = sales_functions.generate_location_map(query="Zurich, Switzerland")
    result_data = json.loads(result)

    # Validate successful response
    assert "error" not in result_data
    assert "map_url" in result_data
    assert "coordinates" in result_data
    assert "latitude" in result_data["coordinates"]
    assert "longitude" in result_data["coordinates"]
    assert result_data["location_name"] == "Zurich, Switzerland"

    # Verify map URL structure
    assert "atlas.microsoft.com/map/static/png" in result_data["map_url"]


@pytest.mark.integration
def test_real_generate_location_map_with_coordinates(has_azure_maps_key):
    """Test generate_location_map with coordinates using the real Azure Maps API."""
    # Use the API key to avoid 'not accessed' warning
    assert has_azure_maps_key is not None
    # Use Zurich coordinates
    lat = 47.3769
    lon = 8.5417

    # Call function with coordinates
    result = sales_functions.generate_location_map(lat=lat, lon=lon)
    result_data = json.loads(result)

    # Validate successful response
    assert "error" not in result_data
    assert "map_url" in result_data
    assert "coordinates" in result_data
    assert result_data["coordinates"]["latitude"] == lat
    assert result_data["coordinates"]["longitude"] == lon

    # Verify map URL contains the correct coordinates (handle URL-encoded comma)
    assert f"center={lon},{lat}" in result_data["map_url"] or f"center={lon}%2C{lat}" in result_data["map_url"]


@pytest.mark.integration
def test_real_workflow_with_clients(has_azure_maps_key):
    """Test a complete workflow using real API calls."""
    # Reset global state
    sales_functions.reset_sales_day()

    # Step 1: Get today's clients
    clients_result = sales_functions.get_clients_for_today()
    clients_data = json.loads(clients_result)
    assert "error" not in clients_data
    assert "clients" in clients_data
    assert len(clients_data["clients"]) > 0

    # Step 2: Plan optimal route
    route_result = sales_functions.plan_optimal_route()
    route_data = json.loads(route_result)
    assert "error" not in route_data
    assert "routes" in route_data

    # Step 3: Get first client visit
    visit_result = sales_functions.get_next_visit()
    visit_data = json.loads(visit_result)
    assert "error" not in visit_data
    assert "client_name" in visit_data
    assert "status" in visit_data
    assert visit_data["status"] == "in_progress"

    # Step 4: Check status
    status_result = sales_functions.get_current_visit_status()
    status_data = json.loads(status_result)
    assert "error" not in status_data
    assert status_data["status"] == "in_progress"
    assert "client_name" in status_data

    # Step 5: Get map for current location
    map_result = sales_functions.generate_location_map()
    map_data = json.loads(map_result)
    assert "error" not in map_data
    assert "map_url" in map_data

    # Step 6: Reset at the end
    reset_result = sales_functions.reset_sales_day()
    reset_data = json.loads(reset_result)
    assert reset_data["status"] == "success"
