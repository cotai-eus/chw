"""
Rate limiting middleware using Redis for distributed rate limiting.
"""
import time
import logging
from typing import Optional, Dict, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_settings
from app.db.session import get_redis
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitRule:
    """Rate limiting rule configuration."""
    
    def __init__(
        self,
        requests: int,
        window: int,
        per: str = "ip",  # ip, user, endpoint
        burst: Optional[int] = None
    ):
        self.requests = requests
        self.window = window  # in seconds
        self.per = per
        self.burst = burst or requests


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Redis-based distributed rate limiting middleware.
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # Default rate limiting rules
        self.default_rules = {
            "global": RateLimitRule(requests=1000, window=3600, per="ip"),  # 1000 req/hour per IP
            "auth": RateLimitRule(requests=10, window=900, per="ip"),  # 10 auth attempts per 15 min
            "api": RateLimitRule(requests=100, window=300, per="user"),  # 100 req per 5 min per user
            "upload": RateLimitRule(requests=20, window=3600, per="user"),  # 20 uploads per hour
            "websocket": RateLimitRule(requests=5, window=60, per="ip"),  # 5 WS connections per minute
        }
        
        # Endpoint-specific rules
        self.endpoint_rules = {
            "/api/v1/auth/login": "auth",
            "/api/v1/auth/register": "auth",
            "/api/v1/auth/refresh": "auth",
            "/api/v1/files/upload": "upload",
            "/ws/": "websocket",
        }
        
        # Excluded paths (no rate limiting)
        self.excluded_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to request."""
        
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        try:
            # Determine which rule to apply
            rule_name = self.get_rule_for_request(request)
            rule = self.default_rules.get(rule_name, self.default_rules["global"])
            
            # Get rate limit key
            limit_key = await self.get_rate_limit_key(request, rule)
            
            # Check rate limit
            allowed, remaining, reset_time = await self.check_rate_limit(limit_key, rule)
            
            if not allowed:
                # Rate limit exceeded
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "retry_after": reset_time
                    },
                    headers={
                        "X-RateLimit-Limit": str(rule.requests),
                        "X-RateLimit-Remaining": str(remaining),
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time)
                    }
                )
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(rule.requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in rate limit middleware: {e}")
            # Continue with request if middleware fails
            return await call_next(request)
    
    def get_rule_for_request(self, request: Request) -> str:
        """Determine which rate limiting rule to apply."""
        path = request.url.path
        
        # Check for specific endpoint rules
        for endpoint_prefix, rule_name in self.endpoint_rules.items():
            if path.startswith(endpoint_prefix):
                return rule_name
        
        # Default to API rule for API endpoints
        if path.startswith("/api/"):
            return "api"
        
        # Default global rule
        return "global"
    
    async def get_rate_limit_key(self, request: Request, rule: RateLimitRule) -> str:
        """Generate rate limit key based on rule configuration."""
        base_key = "rate_limit"
        
        if rule.per == "ip":
            client_ip = self.get_client_ip(request)
            return f"{base_key}:ip:{client_ip}:{rule.window}"
        
        elif rule.per == "user":
            user_id = await self.get_user_id_from_request(request)
            if user_id:
                return f"{base_key}:user:{user_id}:{rule.window}"
            else:
                # Fallback to IP if no user
                client_ip = self.get_client_ip(request)
                return f"{base_key}:ip:{client_ip}:{rule.window}"
        
        elif rule.per == "endpoint":
            endpoint = request.url.path
            client_ip = self.get_client_ip(request)
            return f"{base_key}:endpoint:{endpoint}:ip:{client_ip}:{rule.window}"
        
        else:
            # Default to IP
            client_ip = self.get_client_ip(request)
            return f"{base_key}:ip:{client_ip}:{rule.window}"
    
    async def get_user_id_from_request(self, request: Request) -> Optional[str]:
        """Extract user ID from request token."""
        try:
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            token = authorization.split(" ")[1]
            payload = decode_access_token(token)
            return payload.get("sub")
        except Exception:
            return None
    
    def get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    async def check_rate_limit(
        self,
        key: str,
        rule: RateLimitRule
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit using sliding window algorithm.
        Returns: (allowed, remaining_requests, reset_time)
        """
        try:
            redis = await get_redis()
            current_time = int(time.time())
            window_start = current_time - rule.window
            
            # Use sliding window with Redis sorted sets
            pipe = redis.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, rule.window + 10)  # Extra time for cleanup
            
            results = await pipe.execute()
            current_requests = results[1] + 1  # +1 for the current request
            
            # Calculate remaining and reset time
            remaining = max(0, rule.requests - current_requests)
            reset_time = current_time + rule.window
            
            # Check if limit exceeded
            allowed = current_requests <= rule.requests
            
            if not allowed:
                # Remove the current request since it's not allowed
                await redis.zrem(key, str(current_time))
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Allow request if Redis fails
            return True, rule.requests, int(time.time()) + rule.window


class BurstRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Burst rate limiting middleware for handling sudden spikes.
    """
    
    def __init__(self, app, burst_limit: int = 50, burst_window: int = 60):
        super().__init__(app)
        self.burst_limit = burst_limit
        self.burst_window = burst_window
    
    async def dispatch(self, request: Request, call_next):
        """Apply burst rate limiting."""
        try:
            client_ip = self.get_client_ip(request)
            burst_key = f"burst_limit:ip:{client_ip}"
            
            redis = await get_redis()
            current_time = int(time.time())
            
            # Check burst limit
            current_burst = await redis.incr(burst_key)
            
            if current_burst == 1:
                # First request in burst window
                await redis.expire(burst_key, self.burst_window)
            
            if current_burst > self.burst_limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Burst rate limit exceeded",
                        "retry_after": self.burst_window
                    },
                    headers={
                        "X-Burst-Limit": str(self.burst_limit),
                        "X-Burst-Remaining": "0",
                        "Retry-After": str(self.burst_window)
                    }
                )
            
            response = await call_next(request)
            
            # Add burst limit headers
            response.headers["X-Burst-Limit"] = str(self.burst_limit)
            response.headers["X-Burst-Remaining"] = str(max(0, self.burst_limit - current_burst))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in burst rate limit middleware: {e}")
            return await call_next(request)
    
    def get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class AdaptiveRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Adaptive rate limiting that adjusts limits based on server load.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.base_limit = 100
        self.load_threshold = 0.8
    
    async def dispatch(self, request: Request, call_next):
        """Apply adaptive rate limiting based on server load."""
        try:
            # Get current server metrics (simplified)
            server_load = await self.get_server_load()
            
            # Adjust rate limit based on load
            if server_load > self.load_threshold:
                # Reduce rate limit when server is under stress
                adjusted_limit = int(self.base_limit * (1 - server_load))
                request.state.adaptive_limit = max(10, adjusted_limit)
            else:
                request.state.adaptive_limit = self.base_limit
            
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Error in adaptive rate limit middleware: {e}")
            return await call_next(request)
    
    async def get_server_load(self) -> float:
        """Get current server load (simplified metric)."""
        try:
            # This is a simplified implementation
            # In production, you might use system metrics, queue lengths, etc.
            redis = await get_redis()
            
            # Count active connections or requests
            active_connections = await redis.get("active_connections") or 0
            max_connections = 1000  # Configure based on your server capacity
            
            return int(active_connections) / max_connections
            
        except Exception:
            return 0.0  # Default to no load if metrics unavailable
