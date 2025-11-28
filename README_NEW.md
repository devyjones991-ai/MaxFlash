# MaxFlash Trading System

Crypto trading bot with scam detection, signals, and autotrading.

## Features

- **Scam Detection**: Analyze tokens on DEX (Uniswap v3, PancakeSwap) for scam indicators
- **Trading Signals**: Generate and rank signals (Free/Pro/Alpha tiers)
- **Auto Trading**: Automated trading on Binance Spot with self-learning capabilities
- **Telegram Bot**: Signal delivery and subscription management

## Architecture

- **Backend**: FastAPI + PostgreSQL + Redis
- **DEX Analysis**: Uniswap v3 (Ethereum), PancakeSwap (BSC)
- **CEX Trading**: Binance Spot
- **ML**: XGBoost/LightGBM for scam detection and signal ranking
- **Optimization**: Cython for performance-critical code

## Quick Start

1. Copy `.env.example` to `.env` and configure
2. Start services: `docker-compose -f infra/docker-compose.yml up -d`
3. Run migrations: `alembic upgrade head`
4. Start API: `uvicorn app.main:app --reload`

## Project Structure

```
app/              # FastAPI application
services/         # Business logic services
  dex_ingest/     # DEX data ingestion
  scam_detector/  # Scam detection
  signals/        # Signal generation
  trading/        # Auto trading
  learning/       # Self-learning
bots/             # Telegram bot
ml/               # ML models and feature store
cython_ext/       # Cython optimizations
infra/            # Docker and infrastructure
scripts/          # Utility scripts
```

## License

MIT

