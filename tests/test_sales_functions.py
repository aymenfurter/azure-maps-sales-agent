"""
Unit tests for sales_functions.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock
import sales_functions
from mock_api import SAMPLE_CLIENTS, OFFICE_LOCATION


class MockResponse:
    """Mock class for requests.Response."""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)
    
    def json(self):
        return self.json_data


@pytest.fixture
def reset_globals():
    """Reset the global variables in sales_functions before each test."""
    sales_functions.current_route = None
    sales_functions.current_client_list = None
    sales_functions.current_visit_index = -1
    sales_functions.map_cache = {}
    yield


def test_get_azure_maps_key(mock_env_azure_maps_key):
    """Test retrieving Azure Maps API key from environment variables."""
    key = sales_functions.get_azure_maps_key()
    assert key == "mock_azure_maps_key_for_testing"


def test_format_coordinates_for_azure_maps():
    """Test formatting client coordinates for Azure Maps API."""
    # Create test clients
    test_clients = [
        {
            "coordinates": {
                "latitude": 47.1234,
                "longitude": 8.5678
            }
        },
        {
            "coordinates": {
                "latitude": 46.7890,
                "longitude": 9.1234
            }
        }
    ]
    
    # Format coordinates
    result = sales_functions.format_coordinates_for_azure_maps(test_clients)
    
    # Expected format: "office_lat,office_lon:client1_lat,client1_lon:client2_lat,client2_lon:office_lat,office_lon"
    expected_parts = [
        f"{OFFICE_LOCATION['coordinates']['latitude']},{OFFICE_LOCATION['coordinates']['longitude']}",
        "47.1234,8.5678",
        "46.789,9.1234",
        f"{OFFICE_LOCATION['coordinates']['latitude']},{OFFICE_LOCATION['coordinates']['longitude']}"
    ]
    expected = ":".join(expected_parts)
    
    assert result == expected


@patch("sales_functions.get_todays_clients")
def test_get_clients_for_today_success(mock_get_todays_clients, reset_globals):
    """Test get_clients_for_today with successful response."""
    # Mock the API response
    mock_response = {
        "date": "2023-07-15",
        "office": OFFICE_LOCATION,
        "clients": SAMPLE_CLIENTS[:2]  # First 2 clients
    }
    mock_get_todays_clients.return_value = mock_response
    
    # Call the function
    result = sales_functions.get_clients_for_today()
    result_data = json.loads(result)
    
    # Validate result
    assert "date" in result_data
    assert result_data["date"] == "2023-07-15"
    assert "client_count" in result_data
    assert result_data["client_count"] == 2
    assert "clients" in result_data
    assert len(result_data["clients"]) == 2
    
    # Check that clients are correctly formatted
    for client in result_data["clients"]:
        assert "id" in client
        assert "name" in client
        assert "address" in client
        assert "contact" in client
        assert "priority" in client
    
    # Check that global state is updated
    assert sales_functions.current_client_list == SAMPLE_CLIENTS[:2]
    assert sales_functions.current_visit_index == -1


@patch("sales_functions.get_todays_clients")
def test_get_clients_for_today_error(mock_get_todays_clients, reset_globals):
    """Test get_clients_for_today with an error."""
    # Mock an exception
    mock_get_todays_clients.side_effect = Exception("API connection failed")
    
    # Call the function
    result = sales_functions.get_clients_for_today()
    result_data = json.loads(result)
    
    # Validate error response
    assert "error" in result_data
    assert "API connection failed" in result_data["error"]


@patch("sales_functions.get_clients_for_today")
@patch("requests.get")
@patch("sales_functions.get_azure_maps_key")
def test_plan_optimal_route_success(mock_get_key, mock_requests_get, mock_get_clients, reset_globals):
    """Test plan_optimal_route with successful API response."""
    # Setup mocks
    mock_get_key.return_value = "test_key"
    
    # Set up current_client_list
    sales_functions.current_client_list = SAMPLE_CLIENTS[:2]
    
    # Mock successful Azure Maps API response
    mock_api_response = {
        "routes": [
            {
                "summary": {
                    "lengthInMeters": 15000,
                    "travelTimeInSeconds": 1800,
                    "trafficDelayInSeconds": 120
                },
                "legs": [
                    {
                        "summary": {
                            "lengthInMeters": 5000,
                            "travelTimeInSeconds": 600
                        },
                        "points": [] # Would have many points in real response
                    },
                    {
                        "summary": {
                            "lengthInMeters": 10000,
                            "travelTimeInSeconds": 1200
                        },
                        "points": [] # Would have many points in real response
                    }
                ],
                "sections": [],
                "guidance": {
                    "instructions": []
                }
            }
        ]
    }
    mock_requests_get.return_value = MockResponse(mock_api_response)
    
    # Call the function
    result = sales_functions.plan_optimal_route()
    result_data = json.loads(result)
    
    # Validate response
    assert "routes" in result_data
    assert len(result_data["routes"]) == 1
    assert "legs" in result_data["routes"][0]
    assert len(result_data["routes"][0]["legs"]) == 2
    
    # Verify points were cleaned up
    for leg in result_data["routes"][0]["legs"]:
        assert "points" not in leg


@patch("requests.get")
@patch("sales_functions.get_azure_maps_key")
def test_plan_optimal_route_api_error(mock_get_key, mock_requests_get, reset_globals):
    """Test plan_optimal_route with API error."""
    # Setup mocks
    mock_get_key.return_value = "test_key"
    
    # Set up current_client_list
    sales_functions.current_client_list = SAMPLE_CLIENTS[:2]
    
    # Mock API error response
    mock_requests_get.return_value = MockResponse({"error": {"code": "400", "message": "Invalid parameter"}}, 400)
    
    # Call the function
    result = sales_functions.plan_optimal_route()
    result_data = json.loads(result)
    
    # Validate error response
    assert "error" in result_data


@patch("sales_functions.get_client_details")
def test_get_next_visit(mock_get_client_details, reset_globals):
    """Test get_next_visit function."""
    # Setup
    sales_functions.current_client_list = SAMPLE_CLIENTS[:3]
    sales_functions.current_visit_index = -1
    
    # Mock client details
    mock_client_details = {
        **SAMPLE_CLIENTS[0],
        "last_visit": "2023-06-15",
        "notes": "Interested in new product line"
    }
    mock_get_client_details.return_value = mock_client_details
    
    # Test first visit
    result = sales_functions.get_next_visit()
    result_data = json.loads(result)
    
    # Validate
    assert result_data["visit_number"] == 1
    assert result_data["total_visits"] == 3
    assert result_data["client_id"] == SAMPLE_CLIENTS[0]["id"]
    assert result_data["client_name"] == SAMPLE_CLIENTS[0]["name"]
    assert result_data["last_visit"] == "2023-06-15"
    assert result_data["notes"] == "Interested in new product line"
    assert result_data["status"] == "in_progress"
    
    # Check that index was incremented
    assert sales_functions.current_visit_index == 0


def test_get_next_visit_completed(reset_globals):
    """Test get_next_visit when all visits are completed."""
    # Setup - all visits completed
    sales_functions.current_client_list = SAMPLE_CLIENTS[:2]
    sales_functions.current_visit_index = 2  # Past the end of the list
    
    # Call function
    result = sales_functions.get_next_visit()
    result_data = json.loads(result)
    
    # Validate completion message
    assert "message" in result_data
    assert "completed" in result_data["message"]
    assert result_data["location"] == "Office"
    assert result_data["status"] == "completed"


def test_get_current_visit_status(reset_globals):
    """Test get_current_visit_status in different states."""
    # Test 1: Not started
    sales_functions.current_client_list = SAMPLE_CLIENTS[:3]
    sales_functions.current_visit_index = -1
    
    result = sales_functions.get_current_visit_status()
    result_data = json.loads(result)
    
    assert result_data["message"].startswith("Sales day not yet started")
    assert result_data["status"] == "not_started"
    assert result_data["location"] == "Office"
    
    # Test 2: In progress
    sales_functions.current_visit_index = 1  # Second client
    
    result = sales_functions.get_current_visit_status()
    result_data = json.loads(result)
    
    assert "message" in result_data
    assert result_data["visit_number"] == 2
    assert result_data["total_visits"] == 3
    assert result_data["remaining_visits"] == 1
    assert result_data["client_id"] == SAMPLE_CLIENTS[1]["id"]
    assert result_data["status"] == "in_progress"
    
    # Test 3: Completed
    sales_functions.current_visit_index = 3  # Past end of list
    
    result = sales_functions.get_current_visit_status()
    result_data = json.loads(result)
    
    assert result_data["message"].startswith("All client visits completed")
    assert result_data["status"] == "completed"
    assert "summary" in result_data
    assert result_data["summary"]["total_visits"] == 3


@patch("requests.get")
@patch("sales_functions.get_azure_maps_key")
def test_generate_location_map_with_query(mock_get_key, mock_requests_get, reset_globals):
    """Test generate_location_map with query parameter."""
    # Setup mocks
    mock_get_key.return_value = "test_key"
    
    # Mock geocode API response
    geocode_response = {
        "results": [
            {
                "position": {
                    "lat": 47.3698,
                    "lon": 8.5392
                }
            }
        ]
    }
    mock_requests_get.return_value = MockResponse(geocode_response)
    
    # Call function with query
    result = sales_functions.generate_location_map(query="Zurich, Switzerland")
    result_data = json.loads(result)
    
    # Validate result
    assert "location_name" in result_data
    assert result_data["location_name"] == "Zurich, Switzerland"
    assert "map_url" in result_data
    assert "coordinates" in result_data
    assert "latitude" in result_data["coordinates"]
    assert "longitude" in result_data["coordinates"]
    assert "_chat_display" in result_data
    assert result_data["_chat_display"]["type"] == "image"


def test_reset_sales_day(reset_globals):
    """Test reset_sales_day function."""
    # Setup some state
    sales_functions.current_route = {"some": "route"}
    sales_functions.current_client_list = SAMPLE_CLIENTS
    sales_functions.current_visit_index = 2
    
    # Call reset
    result = sales_functions.reset_sales_day()
    result_data = json.loads(result)
    
    # Validate response
    assert "message" in result_data
    assert "reset" in result_data["message"]
    assert result_data["status"] == "success"
    
    # Check globals were reset
    assert sales_functions.current_route is None
    assert sales_functions.current_client_list is None
    assert sales_functions.current_visit_index == -1