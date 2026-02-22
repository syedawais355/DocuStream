import json
import time
import uuid
from contextvars import ContextVar
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from logger import get_logger

logger = get_logger()
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_var.set(correlation_id)
        
        start_time = time.time()
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        log_record = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "correlation_id": correlation_id,
        }
        logger.info(json.dumps(log_record))
        
        response.headers["X-Correlation-ID"] = correlation_id
        return response
