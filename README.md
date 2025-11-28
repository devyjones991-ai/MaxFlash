# MaxFlash Trading System

MaxFlash is an advanced crypto trading bot with AI-powered signal analysis, a web dashboard, and Telegram integration.

## 🏗 Architecture

The system consists of several interconnected components:

1. **Core Application (`app/`)**:
    - **Database**: PostgreSQL (async via SQLAlchemy) for storing users, signals, and market data.
    - **Config**: Single source of truth in `app/config.py`.
    - **LLM Engine**: Connects to a local LLM (Ollama) for market analysis.

2. **Telegram Bot (`bots/telegram/`)**:
    - Runs as a separate process.
    - Provides a menu-driven interface for users.
    - Commands: `/start`, `/signals`, `/analyze`, `/status`.
    - **Flow**: User requests analysis -> Bot asks for symbol -> LLM processes request -> Result sent to user.

3. **Web Dashboard (`web_interface/`)**:
    - Built with Dash/Plotly.
    - Visualizes market data, signals, and account status.
    - Accessible at `http://<server-ip>:8050`.

4. **MCP Server (`mcp_server.py`)**:
    - Model Context Protocol server for AI agent integration.
    - Exposes tools for market data and trading.

## ⚙️ Configuration

All configuration is consolidated in `app/config.py`.
Environment variables are loaded from `.env`.

**Key Settings:**

- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.
- `DATABASE_URL`: Connection string for PostgreSQL.
- `USE_LOCAL_LLM`: Enable/disable local LLM (Ollama).
- `OLLAMA_BASE_URL`: URL for Ollama (default: `http://localhost:11434`).

## 🚀 Running the Project

To start all services (Dashboard, Bot, MCP):

```bash
python run.py
```

This script manages the processes and ensures everything starts in the correct order.

## 🛠 Troubleshooting

- **Bot not responding?** Check `logs/maxflash.log`. Ensure `run_bot.py` is running.
- **Dashboard not loading?** Check port 8050 and firewall settings.
- **LLM errors?** Ensure Ollama is running (`ollama serve`) and the model `qwen2.5:7b` is pulled.
