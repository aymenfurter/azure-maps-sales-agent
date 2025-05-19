"""
Sales functions for route planning and client visits using Azure Maps.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from mock_api import OFFICE_LOCATION, get_client_details, get_todays_clients

# Load environment variables from .env file
load_dotenv()


# Route planning variables
current_route = None
current_client_list = None
current_visit_index = -1  # -1 means at office, not yet started

# Cache for maps to avoid unnecessary API calls
map_cache = {}


def get_azure_maps_key() -> str:
    """Get the Azure Maps API key from environment variables."""
    return os.environ.get("AZURE_MAPS_KEY", "")


def format_coordinates_for_azure_maps(clients: List[Dict]) -> str:
    """
    Format client coordinates for Azure Maps API.

    Args:
        clients: List of client dictionaries with coordinates

    Returns:
        String formatted for Azure Maps Route API
    """
    # Start with office coordinates
    coordinates = [f"{OFFICE_LOCATION['coordinates']['latitude']},{OFFICE_LOCATION['coordinates']['longitude']}"]

    # Add all client coordinates
    for client in clients:
        coordinates.append(f"{client['coordinates']['latitude']},{client['coordinates']['longitude']}")

    # End back at the office
    coordinates.append(f"{OFFICE_LOCATION['coordinates']['latitude']},{OFFICE_LOCATION['coordinates']['longitude']}")

    return ":".join(coordinates)


def get_clients_for_today() -> str:
    """
    Get the list of clients to visit today.

    Returns:
        JSON string with client information
    """
    # Reset current state
    global current_visit_index, current_client_list
    current_visit_index = -1

    try:
        # Call the mock API
        result = get_todays_clients(count=4)  # Get 4 clients for today
        current_client_list = result["clients"]

        # Format the result for display
        formatted_result = {
            "date": result["date"],
            "client_count": len(result["clients"]),
            "clients": [
                {
                    "id": client["id"],
                    "name": client["name"],
                    "address": client["address"],
                    "contact": client["contact"],
                    "priority": client["priority"],
                }
                for client in result["clients"]
            ],
        }

        return json.dumps(formatted_result)

    except Exception as e:
        error_msg = f"Error retrieving today's clients: {str(e)}"
        return json.dumps({"error": error_msg})


def plan_optimal_route() -> str:
    """
    Plan an optimal route for today's clients using Azure Maps.

    Returns:
        JSON string with the planned route information
    """
    global current_route

    try:
        # Check if we have clients
        if not current_client_list:
            clients_today_result = get_clients_for_today()
            clients_today_data = json.loads(clients_today_result)
            if "error" in clients_today_data:
                return clients_today_result

            # If still no clients after getting today's list
            if not current_client_list:
                return json.dumps(
                    {
                        "message": "No clients scheduled for today.",
                        "total_distance_km": 0,
                        "total_duration_minutes": 0,
                        "start_time": datetime.now().strftime("%H:%M"),
                        "end_time": datetime.now().strftime("%H:%M"),
                        "optimized_client_order": [],
                        "itinerary": [
                            {
                                "leg_number": 1,
                                "origin": OFFICE_LOCATION["name"],
                                "origin_address": OFFICE_LOCATION["address"],
                                "destination": OFFICE_LOCATION["name"],
                                "destination_address": OFFICE_LOCATION["address"],
                                "distance_km": 0,
                                "duration_minutes": 0,
                                "travel_instructions": ["Remain at office - no client visits scheduled"],
                            }
                        ],
                    }
                )

        # Get Azure Maps key
        azure_maps_key = get_azure_maps_key()
        if not azure_maps_key:
            error_msg = "Azure Maps API key not found in environment variables"
            return json.dumps({"error": error_msg})

        # Make a copy of the current client list to preserve original order for indexing
        original_clients_for_route = list(current_client_list)
        if not original_clients_for_route:
            return json.dumps({"message": "No clients to plan a route for.", "itinerary": []})

        # Format coordinates for Azure Maps
        coordinates_query = format_coordinates_for_azure_maps(original_clients_for_route)

        # Prepare request to Azure Maps Route API
        url = "https://atlas.microsoft.com/route/directions/json"
        params = {
            "subscription-key": azure_maps_key,
            "api-version": "1.0",
            "query": coordinates_query,
            "computeBestOrder": "true",
            "routeType": "fastest",
            "traffic": "true",
            "travelMode": "car",
            "instructionsType": "text",
            "computeTravelTimeFor": "all",
        }

        print(f"Requesting route with params: {params}")

        response = requests.get(url, params=params)

        # First check HTTP status code
        if response.status_code != 200:
            error_msg = f"Azure Maps API request failed with status {response.status_code}"
            return json.dumps({"error": error_msg})

        response_data = response.json()

        # Validate response structure
        if not response_data:
            return json.dumps({"error": "Empty response from Azure Maps API"})

        # Check for API error response
        if "error" in response_data:
            error_detail = response_data.get("error", {})
            error_code = error_detail.get("code", "unknown")
            error_message = error_detail.get("message", "Unknown Azure Maps API error")
            return json.dumps({"error": f"Azure Maps API error: {error_code} - {error_message}", "request_params": params})

        # Validate route data
        routes = response_data.get("routes", [])
        if not routes:
            return json.dumps({"error": "No route data received from Azure Maps API", "api_response": response_data})

        # Process route data - clean up large point arrays
        for route in response_data["routes"]:
            for leg in route["legs"]:
                leg.pop("points", None)

        # Save the route data
        global current_route
        current_route = response_data

        # Log the processed response for debugging
        with open("route_response.json", "w") as f:
            json.dump(response_data, f, indent=2)

        return json.dumps(response_data)

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error while calling Azure Maps API: {str(e)}"
        return json.dumps({"error": error_msg})
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response from Azure Maps API: {str(e)}"
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Unexpected error planning route: {str(e)}"
        return json.dumps({"error": error_msg})


def get_next_visit() -> str:
    """
    Get information about the next client to visit.

    Returns:
        JSON string with next visit information
    """
    global current_visit_index

    try:
        # Check if we have a route planned
        if not current_client_list:
            plan_result = plan_optimal_route()
            plan_data = json.loads(plan_result)
            if "error" in plan_data:
                return plan_result

        # Increment the visit index
        current_visit_index += 1

        # Check if we've completed all visits
        if current_visit_index >= len(current_client_list):
            return json.dumps(
                {
                    "message": "All client visits completed. Returning to office.",
                    "location": "Office",
                    "address": OFFICE_LOCATION["address"],
                    "status": "completed",
                }
            )

        # Get the next client
        next_client = current_client_list[current_visit_index]

        # Get additional details
        client_details = get_client_details(next_client["id"])

        # Format the result
        result = {
            "visit_number": current_visit_index + 1,
            "total_visits": len(current_client_list),
            "client_id": next_client["id"],
            "client_name": next_client["name"],
            "contact_person": next_client["contact"],
            "address": next_client["address"],
            "coordinates": next_client["coordinates"],
            "priority": next_client["priority"],
            "last_visit": client_details.get("last_visit", "Unknown"),
            "notes": client_details.get("notes", "No notes available"),
            "status": "in_progress",
        }

        return json.dumps(result)

    except Exception as e:
        error_msg = f"Error getting next visit: {str(e)}"
        return json.dumps({"error": error_msg})


def get_current_visit_status() -> str:
    """
    Get information about the current visit status.

    Returns:
        JSON string with current visit information
    """

    try:
        # Check if we have a route planned
        if not current_client_list:
            plan_result = plan_optimal_route()
            plan_data = json.loads(plan_result)
            if "error" in plan_data:
                return plan_result

        # Check visit index status
        if current_visit_index < 0:
            # Not started any visits yet
            return json.dumps(
                {
                    "message": "Sales day not yet started. Currently at office.",
                    "location": "Office",
                    "address": OFFICE_LOCATION["address"],
                    "next_action": "Use get_next_visit to start your first client visit",
                    "status": "not_started",
                }
            )
        elif current_visit_index >= len(current_client_list):
            # Completed all visits
            return json.dumps(
                {
                    "message": "All client visits completed. Returned to office.",
                    "location": "Office",
                    "address": OFFICE_LOCATION["address"],
                    "status": "completed",
                    "summary": {
                        "total_visits": len(current_client_list),
                        "clients_visited": [client["name"] for client in current_client_list],
                    },
                }
            )
        else:
            # In progress - get current client
            current_client = current_client_list[current_visit_index]
            remaining = len(current_client_list) - current_visit_index - 1

            result = {
                "message": f"Currently visiting {current_client['name']}",
                "visit_number": current_visit_index + 1,
                "total_visits": len(current_client_list),
                "remaining_visits": remaining,
                "client_id": current_client["id"],
                "client_name": current_client["name"],
                "address": current_client["address"],
                "contact_person": current_client["contact"],
                "next_action": (
                    "Complete this visit and use get_next_visit to proceed to the next client"
                    if remaining > 0
                    else "Complete this visit to finish your sales day"
                ),
                "status": "in_progress",
            }

            return json.dumps(result)

    except Exception as e:
        error_msg = f"Error getting visit status: {str(e)}"
        return json.dumps({"error": error_msg})


def generate_location_map(query: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None) -> str:
    """
    Generate a static map image for a location using Azure Maps.

    Args:
        query: Address or place to generate map for (optional)
        lat: Latitude coordinate (optional, used if query not provided)
        lon: Longitude coordinate (optional, used if query not provided)

    Returns:
        JSON string with the map URL and location details
    """
    try:
        # Check and prepare location parameters
        if not query and (lat is None or lon is None):
            # If no parameters, use current visit location
            if current_client_list and 0 <= current_visit_index < len(current_client_list):
                client = current_client_list[current_visit_index]
                lat = float(client["coordinates"]["latitude"])
                lon = float(client["coordinates"]["longitude"])
                query = client["address"]
                location_name = client["name"]
            else:
                error_msg = "No location specified and no current visit active"
                return json.dumps({"error": error_msg})
        elif query and not lat and not lon:
            # If we only have a query, we need to geocode it first
            geocode_url = "https://atlas.microsoft.com/search/address/json"
            geocode_params = {"subscription-key": get_azure_maps_key(), "api-version": "1.0", "query": query}

            geocode_response = requests.get(geocode_url, params=geocode_params)
            if geocode_response.status_code != 200:
                return json.dumps({"error": f"Geocoding failed: {geocode_response.text}"})

            geocode_data = geocode_response.json()
            if not geocode_data.get("results"):
                return json.dumps({"error": "Location not found"})

            result = geocode_data["results"][0]
            lat = result["position"]["lat"]
            lon = result["position"]["lon"]
            location_name = query
        elif lat is not None and lon is not None:
            location_name = f"Location at {lat}, {lon}"
            if not query:
                query = f"{lat},{lon}"

        # Validate coordinates
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return json.dumps({"error": "Invalid coordinates provided"})

        # Get Azure Maps key
        azure_maps_key = get_azure_maps_key()
        if not azure_maps_key:
            return json.dumps({"error": "Azure Maps API key not found"})

        # Format pin parameters according to Azure Maps API specs
        # Format should be: "default||<lon> <lat>"
        pin_param = f"default||{lon} {lat}"

        # Create map URL with parameters
        params = {
            "subscription-key": azure_maps_key,
            "api-version": "1.0",
            "layer": "basic",
            "zoom": "15",
            "width": "800",
            "height": "600",
            "center": f"{lon},{lat}",
            "pins": pin_param,
        }

        # Build the Azure Maps static image URL
        url = "https://atlas.microsoft.com/map/static/png"
        map_url = f"{url}?{urlencode(params)}"

        # Return the result with the map URL
        result = {
            "location_name": location_name,
            "map_url": map_url,  # Direct URL to the map image
            "coordinates": {"latitude": lat, "longitude": lon},
            "type": "image/png",
            "_chat_display": {"type": "image", "url": map_url, "title": f"Map of {location_name}"},
        }

        return json.dumps(result)

    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Network error: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Error generating map: {str(e)}"})


def reset_sales_day() -> str:
    """
    Reset the current sales day planning.

    Returns:
        JSON string with confirmation message
    """
    global current_route, current_client_list, current_visit_index

    # Reset all globals
    current_route = None
    current_client_list = None
    current_visit_index = -1

    return json.dumps({"message": "Sales day has been reset. You can now plan a new route.", "status": "success"})


def main():
    """Test all Azure Maps functionality."""
    try:
        print("\n1. Testing get_clients_for_today()...")
        clients_result = get_clients_for_today()
        print(json.dumps(json.loads(clients_result), indent=2))

        print("\n2. Testing plan_optimal_route()...")
        route_result = plan_optimal_route()
        print(json.dumps(json.loads(route_result), indent=2))

        print("\n3. Testing get_next_visit() - First client...")
        visit_result = get_next_visit()
        print(json.dumps(json.loads(visit_result), indent=2))

        print("\n4. Testing get_current_visit_status()...")
        status_result = get_current_visit_status()
        print(json.dumps(json.loads(status_result), indent=2))

        print("\n5. Testing generate_location_map() for current location...")
        map_result = generate_location_map()
        map_data = json.loads(map_result)
        if "error" in map_data:
            print("Map error:", map_data["error"])
        else:
            print(f"Map generated successfully for {map_data['location_name']}")
            print(f"Image size: {len(map_data['map_url'])} bytes")

        print("\n6. Testing generate_location_map() with query...")
        map_query_result = generate_location_map(query="Zurich, Switzerland")
        map_query_data = json.loads(map_query_result)
        if "error" in map_query_data:
            print("Map query error:", map_query_data["error"])
        else:
            print(f"Map generated successfully for {map_query_data['location_name']}")
            print(f"Image size: {len(map_query_data['map_url'])} bytes")

        print("\n7. Testing additional visits...")
        for _ in range(2):
            visit_result = get_next_visit()
            print("\nNext visit:")
            print(json.dumps(json.loads(visit_result), indent=2))
            status_result = get_current_visit_status()
            print("\nCurrent status:")
            print(json.dumps(json.loads(status_result), indent=2))

        print("\n8. Testing reset_sales_day()...")
        reset_result = reset_sales_day()
        print(json.dumps(json.loads(reset_result), indent=2))

    except Exception as e:
        print(f"Error during testing: {str(e)}")


if __name__ == "__main__":
    main()
