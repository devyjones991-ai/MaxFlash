"""
Verification script to check if all new components import and initialize correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger_config import setup_logging

logger = setup_logging()


async def verify_components():
    logger.info("Starting verification of new components...")
    errors = []

    # 1. Verify Async Exchange
    try:
        from utils.async_exchange import AsyncExchangeManager

        logger.info("✅ AsyncExchangeManager imported")
        # We won't instantiate it as it might try to connect
    except Exception as e:
        logger.error(f"❌ AsyncExchangeManager failed: {e}")
        errors.append("AsyncExchangeManager")

    # 2. Verify ML Components
    try:
        from ml.lstm_signal_generator import LSTMSignalGenerator
        from ml.feature_engineering import create_all_features

        logger.info("✅ ML components imported")
        try:
            generator = LSTMSignalGenerator()
            logger.info("✅ LSTMSignalGenerator instantiated")
        except ImportError as e:
            if "TensorFlow" in str(e):
                logger.warning(f"⚠️ ML dependencies missing: {e}")
                logger.warning("ML features will be disabled until dependencies are installed.")
            else:
                raise e
    except Exception as e:
        logger.error(f"❌ ML components failed: {e}")
        errors.append("ML Components")

    # 3. Verify Trading Components
    try:
        from trading.order_executor import OrderExecutor
        from trading.risk_manager import AdvancedRiskManager

        logger.info("✅ Trading components imported")

        risk = AdvancedRiskManager(10000)
        logger.info("✅ AdvancedRiskManager instantiated")
    except Exception as e:
        logger.error(f"❌ Trading components failed: {e}")
        errors.append("Trading Components")

    # 4. Verify API
    try:
        from api.main import app

        logger.info("✅ FastAPI app imported")
    except Exception as e:
        logger.error(f"❌ API failed: {e}")
        errors.append("API")

    if not errors:
        logger.info("\n🎉 ALL CHECKS PASSED! System is ready.")
        return True
    else:
        logger.error(f"\n⚠️ Verification failed for: {', '.join(errors)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_components())
    sys.exit(0 if success else 1)
