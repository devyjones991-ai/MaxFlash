"""
Freqtrade REST API клиент для получения данных.
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FreqtradeClient:
    """
    Клиент для взаимодействия с Freqtrade REST API.
    """
    
    def __init__(self, base_url: str = "http://localhost:8080", 
                 username: str = None, password: str = None):
        """
        Инициализация клиента.
        
        Args:
            base_url: URL Freqtrade API (default: http://localhost:8080)
            username: Username для аутентификации (опционально)
            password: Password для аутентификации (опционально)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 5  # 5 секунд timeout
        
        if username and password:
            self.session.auth = (username, password)
    
    def get_status(self) -> Dict:
        """
        Получить статус бота.
        
        Returns:
            Dictionary с статусом
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/status")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting status: {e}")
            return {"error": str(e), "state": "disconnected"}
    
    def get_trades(self, limit: int = 50) -> List[Dict]:
        """
        Получить список сделок.
        
        Args:
            limit: Максимальное количество сделок
            
        Returns:
            List of trades
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/trades",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_open_trades(self) -> List[Dict]:
        """
        Получить открытые сделки.
        
        Returns:
            List of open trades
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/trades/open")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def get_performance(self) -> Dict:
        """
        Получить метрики производительности.
        
        Returns:
            Dictionary с метриками
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/performance")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting performance: {e}")
            return {}
    
    def get_balance(self) -> Dict:
        """
        Получить баланс аккаунта.
        
        Returns:
            Dictionary с балансом
        """
        try:
            response = self.session.get(f"{self.base_url}/api/v1/balance")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting balance: {e}")
            return {}
    
    def is_connected(self) -> bool:
        """
        Проверить подключение к Freqtrade API.
        
        Returns:
            True если подключен
        """
        try:
            status = self.get_status()
            return "error" not in status
        except:
            return False

