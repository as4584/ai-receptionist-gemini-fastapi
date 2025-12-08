from datetime import datetime
from typing import Dict, List, Any, Optional

class Diagnostics:
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.last_error: Optional[Dict[str, Any]] = None
        self.latency_history: List[float] = []
        self.last_twilio_status: str = "unknown"
        self.model_connection_status: bool = False
        self.active_calls: int = 0
        self.total_calls_processed: int = 0
        self.call_history: List[Dict[str, Any]] = []

    def record_call(self, call_data: Dict[str, Any]):
        self.call_history.insert(0, call_data)
        if len(self.call_history) > 50:
            self.call_history.pop()
        
    def record_error(self, error: Exception, context: str = ""):
        self.last_error = {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error),
            "type": type(error).__name__,
            "context": context
        }
        
    def record_latency(self, ms: float):
        self.latency_history.append(ms)
        if len(self.latency_history) > 100:
            self.latency_history.pop(0)
            
    def get_uptime(self) -> str:
        delta = datetime.utcnow() - self.start_time
        return str(delta).split('.')[0]
        
    def get_state(self) -> Dict[str, Any]:
        return {
            "uptime": self.get_uptime(),
            "active_calls": self.active_calls,
            "total_calls": self.total_calls_processed,
            "model_connected": self.model_connection_status,
            "last_twilio_status": self.last_twilio_status,
            "last_error": self.last_error,
            "avg_latency": sum(self.latency_history) / len(self.latency_history) if self.latency_history else 0,
            "recent_calls": self.call_history
        }

# Global instance
diagnostics = Diagnostics()
