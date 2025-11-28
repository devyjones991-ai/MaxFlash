import os
import requests
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)


class LLMEngine:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL_NAME", "qwen2.5:7b")
        self.enabled = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        if not self.enabled:
            return False
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    def analyze_market(self, market_data: Dict[str, Any], prompt_template: str = None) -> str:
        """
        Analyze market data using the local LLM.

        Args:
            market_data: Dictionary containing price, volume, indicators, etc.
            prompt_template: Optional custom prompt.

        Returns:
            String containing the LLM's analysis.
        """
        if not self.is_available():
            return "LLM service is not available or disabled."

        context_str = json.dumps(market_data, indent=2)

        if prompt_template:
            prompt = prompt_template.format(data=context_str)
        else:
            prompt = f"""
            You are an expert crypto trading analyst. Analyze the following market data and provide a trading signal (BUY, SELL, or HOLD) with reasoning.
            
            Market Data:
            {context_str}
            
            Format your response as:
            SIGNAL: [BUY/SELL/HOLD]
            CONFIDENCE: [0-100]%
            REASONING: [Your detailed analysis]
            """

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Low temperature for more deterministic/analytical results
                    "num_ctx": 4096,
                },
            }

            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "No response generated.")

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return f"Error analyzing market: {str(e)}"


# Global instance
llm_engine = LLMEngine()
