# Sales Planning Assistant

A Gradio-based application that uses Azure Maps and Azure AI Projects to help sales representatives plan and execute daily client visits.

## Features
- Retrieve today’s client list.
- Generate an optimized driving route via Azure Maps.
- Track visit progress and show current status.
- Display static map images for any location.
- Reset the sales day at any time.
- Chat interface powered by Azure AI Projects and Gradio.

## Prerequisites
- Python 3.10+
- An Azure subscription (for Maps and AI Projects).
- Azure Maps Key.
- (Optional) Bing Search connection for general questions.

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/aymenfurter/azure-maps-sales-agent.git
cd azure-maps-sales-agent

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy sample .env and fill in your values
cp .env.example .env
# then edit .env with your keys

# 5. Launch the application
python main.py
```

## Environment Variables

Create a `.env` file in the project root (or edit the sample below) and provide the required secrets.

```dotenv
# .env.example
AZURE_MAPS_KEY="YOUR_AZURE_MAPS_PRIMARY_KEY"
PROJECT_CONNECTION_STRING="region.api.azureml.ms;workspace-guid;workspace-name;project-name"
MODEL_DEPLOYMENT_NAME="gpt-4o"
```

> Never commit your real keys to source control.

## Running in Dev Container
A ready-made **Dev Container** is provided. In VS Code:
1. Install the “Dev Containers” extension.
2. Reopen the folder in container.
3. The `postCreateCommand` installs dependencies automatically.

## Running Tests

The project includes a comprehensive test suite using pytest. To run the tests:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=term
```

The tests are also automatically run via GitHub Actions on push and pull requests to the main branch.