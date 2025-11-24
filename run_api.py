"""Simple runner script for the MaxFlash API server."""

import os
import uvicorn

if __name__ == "__main__":
    # Load settings from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"

    print("=" * 80)
    print("MaxFlash Trading System - API Server")
    print("=" * 80)
    print(f"Starting server on http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print(f"Testnet Mode: {os.getenv('USE_TESTNET', 'true')}")
    print("=" * 80)

    uvicorn.run("api.main:app", host=host, port=port, reload=reload)
