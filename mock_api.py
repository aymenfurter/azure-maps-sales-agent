import random
from datetime import datetime
from typing import Any, Dict

# Sample client data with addresses that work with Azure Maps
SAMPLE_CLIENTS = [
    {
        "id": "CL001",
        "name": "Swiss Banking Corp",
        "contact": "Thomas Mueller",
        "address": "Paradeplatz 8, 8001 Zürich",
        "coordinates": {"latitude": 47.369800, "longitude": 8.539185},
        "priority": "high",
    },
    {
        "id": "CL002",
        "name": "Alpine Solutions AG",
        "contact": "Maria Bernhard",
        "address": "Bahnhofstrasse 15, 3920 Zermatt",
        "coordinates": {"latitude": 46.023731, "longitude": 7.747419},
        "priority": "medium",
    },
    {
        "id": "CL003",
        "name": "Geneva Trading SA",
        "contact": "Jean Dupont",
        "address": "Rue du Rhône 30, 1204 Genève",
        "coordinates": {"latitude": 46.203566, "longitude": 6.151768},
        "priority": "high",
    },
]

# Office/starting location
OFFICE_LOCATION = {
    "name": "Office",
    "address": "Stockerstrasse 9, 8002 Zürich",
    "coordinates": {"latitude": 47.366374, "longitude": 8.536213},
}


def get_todays_clients(count: int = 5) -> Dict[str, Any]:
    """
    Simulates an API call to get today's planned client visits.

    Args:
        count: Number of clients to include (default: 5)

    Returns:
        Dict containing today's date, office location, and list of clients
    """
    # Ensure count is reasonable
    count = min(max(2, count), len(SAMPLE_CLIENTS))

    # Select random clients for today, but in a deterministic way based on current date
    today = datetime.now()
    seed = today.year * 10000 + today.month * 100 + today.day
    random.seed(seed)

    # Select clients for today
    todays_clients = random.sample(SAMPLE_CLIENTS, count)

    return {"date": today.strftime("%Y-%m-%d"), "office": OFFICE_LOCATION, "clients": todays_clients}


def get_client_details(client_id: str) -> Dict[str, Any]:
    """
    Simulates an API call to get detailed information about a specific client.

    Args:
        client_id: The ID of the client to retrieve

    Returns:
        Dict containing client details or error message
    """
    for client in SAMPLE_CLIENTS:
        if client["id"] == client_id:
            # Simulate additional information that would come from a real API
            # Generate a random date in the past 15-60 days
            today = datetime.now()
            days_ago = random.randint(15, 60)
            last_visit = today.replace(day=1)  # Move to first day of month
            for _ in range(days_ago):  # Move back one day at a time
                last_visit = last_visit.replace(day=max(1, last_visit.day - 1))
                if last_visit.day == 1:  # If we hit the first of a month
                    if last_visit.month > 1:
                        last_visit = last_visit.replace(month=last_visit.month - 1)
                    else:
                        last_visit = last_visit.replace(year=last_visit.year - 1, month=12)

            additional_info = {
                "last_visit": last_visit.strftime("%Y-%m-%d"),
                "total_purchases": round(random.uniform(5000, 50000), 2),
                "active_contracts": random.randint(1, 3),
                "notes": random.choice(
                    [
                        "Interested in new product line",
                        "Looking to expand current services",
                        "Contract renewal coming up",
                        "Recently upgraded their subscription",
                        "Has open support tickets",
                    ]
                ),
            }

            return {**client, **additional_info}

    return {"error": f"Client with ID {client_id} not found"}
