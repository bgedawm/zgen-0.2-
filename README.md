# Local Scout AI Agent

A powerful AI agent inspired by Scout that runs locally on your machine. This agent can perform a wide range of tasks including information gathering, data processing, document generation, programming tasks, and scheduled automations.

## Features

- **Natural Language Interface**: Interact with the agent using plain English
- **Task Automation**: Schedule recurring tasks or trigger them based on events
- **Tool Integration**: Connect with various tools and APIs for expanded capabilities
- **Web Interface**: User-friendly interface for monitoring and controlling the agent
- **Local Execution**: Runs entirely on your local machine for privacy and security
- **Extensible Architecture**: Easily add new capabilities through the modular design

## Installation

1. Clone this repository:
```bash
https://github.com/bgedawm/zgen0.1.git
cd zgen0.1
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Download the LLM model:
```bash
python scripts/download_model.py
```

## Usage

1. Start the agent:
```bash
python main.py
```

2. Open your browser and navigate to:
```
http://localhost:8001
```

3. Interact with the agent through the web interface or API

## Configuration

Edit the `.env` file to configure:
- LLM settings
- API keys for external services
- Web interface settings
- Logging configuration

## Extending Functionality

The agent is designed to be easily extensible. Check the documentation for guides on:
- Adding new tools
- Creating custom plugins
- Extending the web interface
- Adding scheduled tasks

## Development

1. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black .
isort .
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
