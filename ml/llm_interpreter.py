"""
LLM Interpreter
Interprets technical signals and generates human-readable reasoning.
"""

from typing import Any
from services.llm_engine import llm_engine


class LLMInterpreter:
    """
    Wrapper around LLMEngine to interpret trading signals.
    """

    def __init__(self):
        self.engine = llm_engine

    def interpret_signal(self, symbol: str, signal_type: str, confidence: float, indicators: dict[str, Any]) -> str:
        """
        Generate a natural language explanation for a signal.
        """
        if not self.engine.is_available():
            return "AI reasoning unavailable (LLM disabled)."

        prompt = f"""
        Analyze the following trading signal for {symbol}:
        
        Signal: {signal_type}
        Confidence: {confidence:.2f}
        
        Key Indicators:
        {indicators}
        
        Provide a concise (2-3 sentences) reasoning for this signal. Focus on why the indicators support this direction.
        """

        return self.engine.analyze_market(market_data={}, prompt_template=prompt)
