# Sales Planning Assistant 🗺️🚗

[![Tests and Linting](https://github.com/aymenfurter/azure-maps-sales-agent/actions/workflows/tests.yml/badge.svg)](https://github.com/aymenfurter/azure-maps-sales-agent/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/codecov/c/github/aymenfurter/azure-maps-sales-agent)](https://codecov.io/gh/aymenfurter/azure-maps-sales-agent)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Gradio-based application that leverages Azure Maps and Azure AI Projects to help sales representatives plan and execute daily client visits efficiently.

## 📋 Table of Contents

- [Features](#-features)
- [Technologies Used](#-technologies-used)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [Running in Dev Container](#-running-in-dev-container)
- [Running Tests](#-running-tests)
  - [Integration Tests](#integration-tests)
  - [UI Tests with Playwright](#ui-tests-with-playwright)
  - [Test Coverage](#test-coverage)
  - [Continuous Integration](#continuous-integration)
  - [Linting](#linting)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **Client Management**: Retrieve and manage today's client list
- **Route Optimization**: Generate an optimized driving route via Azure Maps
- **Visit Tracking**: Track visit progress and show current status
- **Location Visualization**: Display static map images for any location
- **Day Management**: Reset the sales day at any time
- **Interactive Chat**: User-friendly chat interface powered by Azure AI Projects and Gradio

## 🛠️ Technologies Used

- **Frontend**: Gradio for interactive UI
- **Maps & Routing**: Azure Maps API
- **AI Integration**: Azure AI Projects
- **Charting**: Plotly
- **Authentication**: Azure Identity
- **Observability**: Azure Monitor OpenTelemetry

## 📋 Prerequisites

- Python 3.10+
- An Azure subscription (for Maps and AI Projects)
- Azure Maps Key
- (Optional) Bing Search connection for general questions

## 🚀 Quick Start

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

## 🔐 Environment Variables

Create a `.env` file in the project root (or edit the sample below) and provide the required secrets.

```dotenv
# .env.example
AZURE_MAPS_KEY="YOUR_AZURE_MAPS_PRIMARY_KEY"
PROJECT_CONNECTION_STRING="region.api.azureml.ms;workspace-guid;workspace-name;project-name"
MODEL_DEPLOYMENT_NAME="gpt-4o"
```

> ⚠️ Never commit your real keys to source control.

## 🐳 Running in Dev Container

A ready-made **Dev Container** is provided. In VS Code:
1. Install the "Dev Containers" extension.
2. Reopen the folder in container.
3. The `postCreateCommand` installs dependencies automatically.

## 🧪 Running Tests

The project includes a comprehensive test suite using pytest. To run the tests:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=term

# Run integration tests (only works with real API keys)
pytest -m integration

# Run UI tests with Playwright
pytest -m ui
```

### Integration Tests

The project includes special integration tests that verify the code works with real API credentials. These tests only run when a valid Azure Maps API key is present in the environment and are skipped otherwise.

To run integration tests:
1. Ensure you have a valid `AZURE_MAPS_KEY` in your environment or .env file
2. Run `pytest -m integration`

These tests make real calls to Azure Maps API services including:
- Route optimization
- Map generation
- Complete workflows

> Note: Integration tests are marked with `@pytest.mark.integration` and are automatically skipped if no valid API key is detected.

### UI Tests with Playwright

The project includes browser-based UI tests that validate the Gradio interface using Playwright. These tests use mocked backend services to avoid making real API calls.

To run UI tests:

```bash
# Install Playwright dependencies
pip install pytest-playwright
playwright install --with-deps chromium

# Run the UI tests
pytest -m ui
```

The UI tests verify:
- Basic interface functionality
- Chat interactions
- Example button clicks
- Tool-based responses (maps, client lists, route planning)

> Note: UI tests are marked with `@pytest.mark.ui` and require Playwright to be installed.

### Test Coverage

The test suite currently achieves the following coverage:

| Module | Coverage |
|--------|----------|
| mock_api.py | 100% |
| sales_functions.py | ~60% |
| initialize.py | 94% |
| chat_ui.py | ~25% |
| Overall | ~60% |

### Continuous Integration

Tests and linting are automatically run via GitHub Actions on push and pull requests to the main branch. The workflow:

1. Sets up a Python environment
2. Installs all dependencies
3. Runs linting checks:
   - flake8: Checks for syntax errors and warnings
   - black: Verifies code style and formatting
   - isort: Ensures imports are sorted properly
4. Runs the test suite with code coverage reporting
5. Runs UI tests with Playwright in a separate job
6. Uploads coverage data to Codecov (if configured)

### Linting

The project uses several linting tools to maintain code quality:

```bash
# Format code with Black
black .

# Sort imports with isort
isort .

# Run flake8 checks
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

Code styling is enforced using:
- **Black**: For consistent code formatting
- **isort**: For organized and consistent import statements
- **flake8**: For detecting syntax errors and style issues

All linting tools are configured with appropriate settings in:
- `setup.cfg`: Configuration for flake8
- `pyproject.toml`: Configuration for Black and isort

You can check the status of builds in the Actions tab of the repository.

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
