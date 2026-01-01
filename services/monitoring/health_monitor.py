"""
Health monitoring service for MaxFlash.
Tracks system health, model performance, and sends alerts.
"""

import os
import json
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import structlog

logger = structlog.get_logger()


class HealthMonitor:
    """Monitor system and model health."""

    def __init__(self, models_dir: str = "models", history_path: str = "models/retrain_history.json"):
        self.models_dir = Path(models_dir)
        self.history_path = Path(history_path)
        self.alerts_sent: Dict[str, datetime] = {}  # Cooldown tracking
        self.alert_cooldown = timedelta(hours=1)  # Don't spam alerts

    def get_system_health(self) -> Dict:
        """Get current system health metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
                'status': 'healthy' if cpu_percent < 90 and memory.percent < 90 else 'warning'
            }
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {'status': 'error', 'error': str(e)}

    def get_model_health(self) -> Dict:
        """Get model health and training statistics."""
        result = {
            'model_exists': False,
            'last_modified': None,
            'model_age_hours': None,
            'recent_accuracy': None,
            'training_history': [],
            'status': 'unknown'
        }

        # Check model file
        model_path = self.models_dir / 'lightgbm_latest.pkl'
        if model_path.exists():
            result['model_exists'] = True
            mtime = datetime.fromtimestamp(model_path.stat().st_mtime)
            result['last_modified'] = mtime.isoformat()
            result['model_age_hours'] = (datetime.now() - mtime).total_seconds() / 3600

        # Load training history
        if self.history_path.exists():
            try:
                with open(self.history_path, 'r') as f:
                    history = json.load(f)

                runs = history.get('runs', [])
                result['training_history'] = runs[-10:]  # Last 10 runs

                # Get recent accuracy
                successful_runs = [r for r in runs if r.get('status') == 'success']
                if successful_runs:
                    latest = successful_runs[-1]
                    result['recent_accuracy'] = latest.get('new_accuracy', 0)
                    result['baseline_accuracy'] = history.get('baseline_accuracy', 0)
                    result['best_accuracy'] = history.get('best_accuracy', 0)

            except Exception as e:
                logger.error(f"Failed to load training history: {e}")

        # Determine status
        if not result['model_exists']:
            result['status'] = 'critical'
        elif result['model_age_hours'] and result['model_age_hours'] > 48:
            result['status'] = 'stale'
        elif result['recent_accuracy'] and result['recent_accuracy'] < 0.45:
            result['status'] = 'degraded'
        else:
            result['status'] = 'healthy'

        return result

    def get_service_status(self) -> Dict:
        """Check if services are running (via process names)."""
        services = {
            'dashboard': False,
            'telegram_bot': False,
        }

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                    if 'dashboard.py' in cmdline:
                        services['dashboard'] = True
                    if 'run_bot.py' in cmdline:
                        services['telegram_bot'] = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.error(f"Failed to check services: {e}")

        return services

    def get_full_health_report(self) -> Dict:
        """Get comprehensive health report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_health(),
            'model': self.get_model_health(),
            'services': self.get_service_status(),
        }

    def format_health_report(self) -> str:
        """Format health report for Telegram message."""
        report = self.get_full_health_report()

        # System section
        sys = report['system']
        sys_emoji = "✅" if sys.get('status') == 'healthy' else "⚠️"
        system_text = (
            f"{sys_emoji} *System*\n"
            f"• CPU: {sys.get('cpu_percent', 'N/A')}%\n"
            f"• Memory: {sys.get('memory_percent', 'N/A')}%\n"
            f"• Disk: {sys.get('disk_percent', 'N/A')}%"
        )

        # Model section
        model = report['model']
        model_emoji = {
            'healthy': '✅',
            'stale': '⚠️',
            'degraded': '🔴',
            'critical': '❌',
            'unknown': '❓'
        }.get(model.get('status'), '❓')

        age_str = f"{model.get('model_age_hours', 0):.1f}h" if model.get('model_age_hours') else "N/A"
        acc_str = f"{model.get('recent_accuracy', 0)*100:.1f}%" if model.get('recent_accuracy') else "N/A"

        model_text = (
            f"\n\n{model_emoji} *Model*\n"
            f"• Status: {model.get('status', 'unknown')}\n"
            f"• Age: {age_str}\n"
            f"• Accuracy: {acc_str}"
        )

        # Services section
        svc = report['services']
        dash_emoji = "✅" if svc.get('dashboard') else "❌"
        bot_emoji = "✅" if svc.get('telegram_bot') else "❌"

        services_text = (
            f"\n\n*Services*\n"
            f"• Dashboard: {dash_emoji}\n"
            f"• Telegram Bot: {bot_emoji}"
        )

        return f"📊 *Health Report*\n\n{system_text}{model_text}{services_text}"

    def check_and_alert(self, send_alert_func) -> List[str]:
        """
        Check health and send alerts if needed.

        Args:
            send_alert_func: Function to send alert message

        Returns:
            List of alerts sent
        """
        alerts = []
        report = self.get_full_health_report()
        now = datetime.now()

        # Check system health
        sys_health = report['system']
        if sys_health.get('cpu_percent', 0) > 90:
            alert_key = 'high_cpu'
            if self._can_send_alert(alert_key):
                send_alert_func(f"⚠️ High CPU usage: {sys_health['cpu_percent']}%")
                alerts.append(alert_key)
                self.alerts_sent[alert_key] = now

        if sys_health.get('memory_percent', 0) > 90:
            alert_key = 'high_memory'
            if self._can_send_alert(alert_key):
                send_alert_func(f"⚠️ High memory usage: {sys_health['memory_percent']}%")
                alerts.append(alert_key)
                self.alerts_sent[alert_key] = now

        # Check model health
        model_health = report['model']
        if model_health.get('status') == 'critical':
            alert_key = 'model_missing'
            if self._can_send_alert(alert_key):
                send_alert_func("❌ Model file is missing! Retraining required.")
                alerts.append(alert_key)
                self.alerts_sent[alert_key] = now

        if model_health.get('status') == 'degraded':
            alert_key = 'model_degraded'
            if self._can_send_alert(alert_key):
                acc = model_health.get('recent_accuracy', 0) * 100
                send_alert_func(f"🔴 Model accuracy degraded: {acc:.1f}%")
                alerts.append(alert_key)
                self.alerts_sent[alert_key] = now

        # Check services
        services = report['services']
        if not services.get('dashboard'):
            alert_key = 'dashboard_down'
            if self._can_send_alert(alert_key):
                send_alert_func("❌ Dashboard service is DOWN!")
                alerts.append(alert_key)
                self.alerts_sent[alert_key] = now

        return alerts

    def _can_send_alert(self, alert_key: str) -> bool:
        """Check if we can send an alert (cooldown check)."""
        if alert_key not in self.alerts_sent:
            return True
        last_sent = self.alerts_sent[alert_key]
        return datetime.now() - last_sent > self.alert_cooldown


# Singleton instance
_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get or create health monitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor





