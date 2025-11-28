import asyncio
import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# Create MCP server
mcp = FastMCP("MaxFlash Trading Tools")


@mcp.tool()
async def get_market_price(symbol: str) -> str:
    """Get the current price of a crypto asset."""
    # In a real scenario, this would query the internal MarketDataManager
    # For now, we return a mock value to demonstrate functionality
    logger.info(f"MCP Tool called: get_market_price({symbol})")
    return f"The current price of {symbol} is $95,000.00 (Mock Data)"


@mcp.tool()
async def get_account_balance() -> str:
    """Get the current account balance."""
    return "Account Balance: $10,000.00 USD"


if __name__ == "__main__":
    logger.info("Starting MaxFlash MCP Server...")
    mcp.run()
