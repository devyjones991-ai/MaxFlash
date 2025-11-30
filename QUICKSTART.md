# Quick Start Guide

## Prerequisites

- Python 3.10+
- Git
- (Optional) Ollama for LLM features

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/devyjones991-ai/MaxFlash.git
    cd MaxFlash
    ```

2. **Create Virtual Environment**:

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configuration**:
    Copy `.env.example` to `.env`:

    ```bash
    cp .env.example .env
    ```

    Edit `.env` and add your Exchange API keys and Telegram Token.

## Running the System

We provide a unified CLI for running all components.

### Start Everything (Bot + Dashboard + MCP)

```bash
python run.py all
```

*Or use the helper scripts:*

- **Windows**: `start.bat`
- **Linux**: `./start.sh`

### Start Individual Components

- **Dashboard only**: `python run.py dashboard`
- **Telegram Bot only**: `python run.py bot`
- **Core Services**: `python run.py core`

## Accessing the Dashboard

Open your browser and navigate to: [http://localhost:8050](http://localhost:8050)

## Troubleshooting

- Check `logs/` for error messages.
- Ensure your `.env` file is correctly configured.
- Refer to [docs/РЕШЕНИЕ_ПРОБЛЕМ.md](docs/РЕШЕНИЕ_ПРОБЛЕМ.md) for common issues.
