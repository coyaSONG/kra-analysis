from fastapi import Request
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Log request
        duration = time.time() - start_time
        print(f"[{request_id}] {request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response