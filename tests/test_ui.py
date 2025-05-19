"""
UI tests for the chat interface using Playwright.

These tests use mocked services for Azure AI Projects to ensure
no real API calls are made during testing.
"""

import os
import signal
import subprocess
import time
from unittest.mock import patch

import pytest
from playwright.sync_api import Page, expect

from tests.mock_services import MockAIProjectClient


@pytest.fixture
def mock_project_client():
    """Return a mocked AIProjectClient."""
    return MockAIProjectClient()


@pytest.fixture(scope="function")
def setup_environment():
    """Set up environment variables needed for testing."""
    with patch.dict(
        os.environ,
        {
            "AZURE_MAPS_KEY": "mock-key-for-testing",
            "PROJECT_CONNECTION_STRING": "mock-connection-string",
            "MODEL_DEPLOYMENT_NAME": "gpt-4o",
            "GRADIO_SERVER_PORT": "7861",  # Use a different port for tests
            "GRADIO_SERVER_NAME": "127.0.0.1",  # Use localhost for tests
        },
    ):
        yield


@pytest.mark.ui
def test_chat_interface_basic_interaction(setup_environment, mock_project_client, page: Page):
    """Test basic interaction with the chat interface."""
    # Mock the required services
    with (
        patch("main.AIProjectClient.from_connection_string", return_value=mock_project_client),
        patch("main.project_client", mock_project_client),
    ):

        # Start the Gradio server in a separate process
        # Launch the server with a 3 second timeout to ensure it starts up
        server = subprocess.Popen(["python", "main.py"], preexec_fn=os.setsid)
        time.sleep(3)  # Wait for the server to start

        try:
            # Visit the Gradio UI
            page.goto("http://127.0.0.1:7861/")

            # Verify the page title
            expect(page.locator("h2")).to_contain_text("Sales Planning Assistant")

            # Check example questions are displayed
            expect(page.locator('button:text("Who are my clients today?")')).to_be_visible()

            # Type a message in the chat input
            chat_input = page.locator("textarea.input-area")
            chat_input.fill("Who are my clients today?")
            chat_input.press("Enter")

            # Wait for the response to appear in the chat
            time.sleep(1)

            # Wait a bit for the full response
            time.sleep(2)

            # Check that the response contains client names
            assistant_message = page.locator(".chat-area .message-wrap:last-child div.agent div.md")
            expect(assistant_message).to_contain_text("your clients for today")

            # Test clicking on example button
            route_button = page.locator('button:text("Plan my optimal rout")')
            route_button.click()

            # Wait for the response
            time.sleep(2)

            # Verify the route planning response
            assistant_message = page.locator(".chat-area .message-wrap:last-child div.agent div.md")
            expect(assistant_message).to_contain_text("planned your optimal route")

            # Test clear chat history
            clear_button = page.locator('button:text("Clear Chat History")')
            clear_button.click()

            # Check that the chat is cleared
            chat_area = page.locator(".chat-area")
            expect(chat_area.locator(".message-wrap")).to_have_count(0)

        finally:
            # Stop the Gradio server
            os.killpg(os.getpgid(server.pid), signal.SIGTERM)


@pytest.mark.ui
def test_chat_interface_tool_interactions(setup_environment, mock_project_client, page: Page):
    """Test interactions with tools in the chat interface."""
    with (
        patch("main.AIProjectClient.from_connection_string", return_value=mock_project_client),
        patch("main.project_client", mock_project_client),
    ):

        server = subprocess.Popen(["python", "main.py"], preexec_fn=os.setsid)
        time.sleep(3)  # Wait for the server to start

        try:
            # Visit the Gradio UI
            page.goto("http://127.0.0.1:7861/")

            # Type a message to request a map
            chat_input = page.locator("textarea.input-area")
            chat_input.fill("Show me a map of my next location")
            chat_input.press("Enter")

            # Wait for the response
            time.sleep(3)

            # Check for the map response
            assistant_message = page.locator(".chat-area .message-wrap:last-child div.agent div.md")
            expect(assistant_message).to_contain_text("Here's a map")

            # Type a message to get the next visit
            chat_input.fill("What is my next visit?")
            chat_input.press("Enter")

            # Wait for the response
            time.sleep(3)

            # Check that we get information about the next client visit
            assistant_message = page.locator(".chat-area .message-wrap:last-child div.agent div.md")
            expect(assistant_message).to_contain_text("Your next visit is")

            # Reset the day
            chat_input.fill("Reset my day")
            chat_input.press("Enter")

            # Wait for the response
            time.sleep(3)

            # Check the reset confirmation
            assistant_message = page.locator(".chat-area .message-wrap:last-child div.agent div.md")
            expect(assistant_message).to_contain_text("Sales day has been reset")

        finally:
            # Stop the Gradio server
            os.killpg(os.getpgid(server.pid), signal.SIGTERM)
