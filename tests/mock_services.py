"""
Mock services for testing, especially UI tests with Playwright.
"""

import json
from unittest.mock import MagicMock, patch

from mock_api import get_client_details, get_todays_clients


class MockThread:
    """Mock implementation of Azure AI Projects Thread."""

    def __init__(self, thread_id="mock-thread-123"):
        self.id = thread_id
        self.status = "active"


class MockAgent:
    """Mock implementation of Azure AI Projects Agent."""

    def __init__(self, agent_id="mock-agent-123", name="mock-sales-agent", model="gpt-4o"):
        self.id = agent_id
        self.name = name
        self.model = model


class MockAgentService:
    """Mock implementation of the agent service from Azure AI Projects."""

    def __init__(self):
        self.agents = {}
        self.threads = {}
        self.messages = {}

    def create_agent(self, model, name, instructions, toolset):
        """Create a mock agent."""
        agent = MockAgent(agent_id=f"agent-{len(self.agents)}", name=name, model=model)
        self.agents[agent.id] = agent
        return agent

    def update_agent(self, assistant_id, model, name, instructions, toolset):
        """Update a mock agent."""
        if assistant_id in self.agents:
            self.agents[assistant_id].model = model
            self.agents[assistant_id].name = name
            return self.agents[assistant_id]
        return self.create_agent(model, name, instructions, toolset)

    def list_agents(self):
        """List all mock agents."""
        return MagicMock(data=list(self.agents.values()))

    def create_thread(self):
        """Create a mock thread."""
        thread = MockThread(thread_id=f"thread-{len(self.threads)}")
        self.threads[thread.id] = thread
        return thread

    def create_message(self, thread_id, role, content):
        """Create a mock message in a thread."""
        if thread_id not in self.messages:
            self.messages[thread_id] = []

        message_id = f"message-{len(self.messages[thread_id])}"
        self.messages[thread_id].append(
            {"id": message_id, "thread_id": thread_id, "role": role, "content": content, "status": "completed"}
        )
        return {"id": message_id}

    def create_stream(self, thread_id, assistant_id, event_handler):
        """Create a mock stream for agent interaction."""
        return MockStream(thread_id, assistant_id, event_handler, self)


class MockMapsService:
    """Mock implementation for Azure Maps services."""

    @staticmethod
    def generate_route():
        """Generate a mock route response."""
        return {
            "routes": [
                {
                    "summary": {
                        "lengthInMeters": 120500,
                        "travelTimeInSeconds": 7500,
                        "trafficDelayInSeconds": 300,
                    },
                    "legs": [
                        {"summary": {"lengthInMeters": 40000, "travelTimeInSeconds": 2500}},
                        {"summary": {"lengthInMeters": 35000, "travelTimeInSeconds": 2200}},
                        {"summary": {"lengthInMeters": 45500, "travelTimeInSeconds": 2800}},
                    ],
                }
            ]
        }

    @staticmethod
    def generate_static_map(lat, lon):
        """Generate a mock static map URL."""
        return f"https://mock.azure.maps.com/map/static/png?center={lon},{lat}&zoom=15&pins=default|{lon}+{lat}"

    @staticmethod
    def geocode_address(query):
        """Generate a mock geocoding response."""
        return {
            "results": [
                {
                    "position": {
                        "lat": 47.3698,
                        "lon": 8.539185,
                    },
                    "address": {
                        "freeformAddress": query if query else "Zurich, Switzerland",
                    },
                }
            ]
        }


class MockStream:
    """Simulate a stream of events from the Azure AI Projects API."""

    def __init__(self, thread_id, assistant_id, event_handler, agent_service):
        self.thread_id = thread_id
        self.assistant_id = assistant_id
        self.event_handler = event_handler
        self.agent_service = agent_service
        self.maps_service = MockMapsService()

        # Pre-defined responses to common queries
        self.responses = {
            "who are my clients today": self._get_clients_response(),
            "plan my optimal route": self._get_route_response(),
            "show me a map": self._get_map_response(),
            "what is my next visit": self._get_next_visit_response(),
            "reset my day": {"message": "Sales day has been reset. You can now plan a new route.", "status": "success"},
        }

    def _get_clients_response(self):
        """Generate a response for the clients list request."""
        result = get_todays_clients(count=3)
        return {
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

    def _get_route_response(self):
        """Generate a response for the route planning request."""
        clients = get_todays_clients(count=3)["clients"]
        route_data = self.maps_service.generate_route()

        return {
            "message": "Route planned successfully",
            "total_distance_km": 120.5,
            "total_duration_minutes": 125,
            "start_time": "09:00",
            "end_time": "17:00",
            "optimized_client_order": [client["name"] for client in clients],
            "routes": route_data["routes"],
        }

    def _get_map_response(self):
        """Generate a mock map response."""
        lat, lon = 47.3698, 8.539185
        mock_map_url = self.maps_service.generate_static_map(lat, lon)

        return {
            "location_name": "Swiss Banking Corp",
            "map_url": mock_map_url,
            "coordinates": {"latitude": lat, "longitude": lon},
            "type": "image/png",
            "_chat_display": {
                "type": "image",
                "url": mock_map_url,
                "title": "Map of Swiss Banking Corp",
            },
        }

    def _get_next_visit_response(self):
        """Generate a response for the next visit request."""
        clients = get_todays_clients(count=3)["clients"]
        client = clients[0]
        client_details = get_client_details(client["id"])

        return {
            "visit_number": 1,
            "total_visits": 3,
            "client_id": client["id"],
            "client_name": client["name"],
            "contact_person": client["contact"],
            "address": client["address"],
            "coordinates": client["coordinates"],
            "priority": client["priority"],
            "last_visit": client_details.get("last_visit", "Unknown"),
            "notes": client_details.get("notes", "No notes available"),
            "status": "in_progress",
        }

    def _find_matching_response(self, user_message):
        """Find a matching response based on user message content."""
        lower_message = user_message.lower()

        # Find the best match based on keywords
        for key in self.responses:
            if key in lower_message:
                return self.responses[key]

        # Default response if no match found
        return {"message": "I understood your request. How can I help you with your sales planning today?"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __iter__(self):
        # Get the most recent user message from thread
        messages = self.agent_service.messages.get(self.thread_id, [])
        if not messages:
            return

        user_messages = [m for m in messages if m["role"] == "user"]
        if not user_messages:
            return

        latest_user_message = user_messages[-1]["content"]
        response = self._find_matching_response(latest_user_message)

        # Create a unique message ID for the response
        message_id = f"response-{len(messages)}"

        # First yield a step delta to indicate tool usage
        if "clients" in response or "routes" in response or "map_url" in response:
            tool_name = (
                "get_clients_for_today"
                if "clients" in response
                else "plan_optimal_route" if "routes" in response else "generate_location_map"
            )
            yield (
                "thread.run.step.delta",
                {
                    "delta": {
                        "step_details": {
                            "type": "tool_calls",
                            "tool_calls": [
                                {"id": "tool-call-1", "type": "function", "function": {"name": tool_name, "arguments": "{}"}}
                            ],
                        }
                    }
                },
            )

            # Then yield a run step completion
            yield (
                "run_step",
                {
                    "id": "step-1",
                    "type": "tool_calls",
                    "status": "completed",
                    "step_details": {
                        "tool_calls": [
                            {
                                "id": "tool-call-1",
                                "type": "function",
                                "function": {"name": tool_name, "output": json.dumps(response)},
                            }
                        ]
                    },
                },
            )

        # Generate assistant message text based on the response content
        text_response = ""
        if "clients" in response:
            clients_list = "\n".join([f"- {client['name']}" for client in response["clients"]])
            text_response = (
                f"Here are your clients for today ({response['date']}):\n\n{clients_list}\n\n"
                "Would you like me to plan your optimal route for the day?"
            )
        elif "routes" in response:
            text_response = (
                f"I've planned your optimal route for today. The total distance is {response['total_distance_km']} km "
                f"and will take about {response['total_duration_minutes']} minutes.\n\n"
                f"The order of visits is: {', '.join(response['optimized_client_order'])}"
            )
        elif "map_url" in response:
            text_response = f"Here's a map showing the location of {response['location_name']}."
        elif "visit_number" in response:
            text_response = (
                f"Your next visit is {response['client_name']} at {response['address']}. "
                f"This is visit {response['visit_number']} out of {response['total_visits']}. "
                f"Note: {response['notes']}"
            )
        else:
            text_response = response.get("message", "How else can I assist you with your sales planning today?")

        # Yield message delta for text chunks (simulating streaming)
        chunk_size = 20
        for i in range(0, len(text_response), chunk_size):
            text_chunk = text_response[i : i + chunk_size]
            yield ("thread.message.delta", {"id": message_id, "delta": {"content": [{"text": {"value": text_chunk}}]}})

        # Finally yield a thread_run completion event
        yield ("thread_run", {"id": "run-1", "status": "completed"})


class MockAIProjectClient:
    """Mock implementation of AIProjectClient."""

    def __init__(self):
        self.agents = MockAgentService()
        self.connections = MagicMock()

    @classmethod
    def from_connection_string(cls, credential, conn_str):
        """Create a client from a connection string."""
        return cls()
