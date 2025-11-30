# MaxFlash Trading System

MaxFlash is an advanced crypto trading bot featuring AI-powered signal analysis, risk management, and a real-time web dashboard.

## Features

- **AI Analysis**: Uses LSTM and Random Forest models for price prediction.
- **LLM Integration**: Explains trading signals using local LLMs (Ollama).
- **Risk Management**: Configurable risk profiles (Aggressive, Balanced, Conservative).
- **Web Dashboard**: Real-time monitoring of signals and bot status.
- **Telegram Bot**: Control the system and receive alerts via Telegram.

## Quick Start

1. **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2. **Configure**:
    Copy `.env.example` to `.env` and set your API keys.

3. **Run**:
    - **Windows**: Double-click `start.bat`
    - **Linux/Mac**: Run `./start.sh`
    - **CLI**: `python run.py all`

## Documentation

- [Quick Start Guide](QUICKSTART.md)
- [Integration Guide](docs/INTEGRATION_GUIDE.md)
- [Optimization Guide](docs/OPTIMIZATION_GUIDE.md)
- [Production Deploy](docs/PRODUCTION_DEPLOY.md)

## Structure

- `app/`: Core application logic and config.
- `bots/`: Telegram bot implementation.
- `ml/`: Machine learning models and signal processing.
- `strategies/`: Trading strategies.
- `trading/`: Signal service and order execution.
- `web_interface/`: Dashboard application.
- `scripts/`: Maintenance and utility scripts.
