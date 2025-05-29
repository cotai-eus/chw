"""
Session control middleware for managing user sessions and concurrent logins.
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.crud.user_session import CRUDUserSession
from app.db.session import get_db
from app.exceptions.custom_exceptions import AuthenticationError

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware to control user sessions and enforce session limits.
    """
    
    def __init__(self, app, max_sessions_per_user: int = 5):
        super().__init__(app)
        self.max_sessions_per_user = max_sessions_per_user
        self.session_crud = CRUDUserSession()
        
        # Routes that don't require session validation
        self.excluded_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/health",
            "/metrics"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate session."""
        
        # Skip session validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Skip for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Get authorization token
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return await call_next(request)
            
            token = authorization.split(" ")[1]
            
            # Decode token to get session info
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            session_id = payload.get("session_id")
            
            if not user_id or not session_id:
                return await call_next(request)
            
            # Validate session in database
            db = next(get_db())
            session = await self.session_crud.get_active_session(db, session_id, user_id)
            
            if not session:
                logger.warning(f"Invalid session {session_id} for user {user_id}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Session expired or invalid"}
                )
            
            # Update session last activity
            await self.session_crud.update_last_activity(db, session_id)
            
            # Add session info to request state
            request.state.user_id = user_id
            request.state.session_id = session_id
            request.state.company_id = payload.get("company_id")
            
            # Check for concurrent session limits
            active_sessions = await self.session_crud.get_user_active_sessions(db, user_id)
            if len(active_sessions) > self.max_sessions_per_user:
                # Deactivate oldest sessions
                await self.cleanup_excess_sessions(db, user_id, active_sessions)
            
            response = await call_next(request)
            
            # Add session headers to response
            response.headers["X-Session-ID"] = session_id
            response.headers["X-Session-Expires"] = session.expires_at.isoformat()
            
            return response
            
        except AuthenticationError as e:
            logger.warning(f"Authentication error in session middleware: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": str(e)}
            )
        except Exception as e:
            logger.error(f"Error in session middleware: {e}")
            # Continue with request if middleware fails
            return await call_next(request)
    
    async def cleanup_excess_sessions(self, db, user_id: str, active_sessions):
        """Remove excess sessions, keeping the most recent ones."""
        try:
            # Sort sessions by last activity (most recent first)
            sorted_sessions = sorted(
                active_sessions,
                key=lambda s: s.last_activity,
                reverse=True
            )
            
            # Keep the most recent sessions, deactivate the rest
            sessions_to_deactivate = sorted_sessions[self.max_sessions_per_user:]
            
            for session in sessions_to_deactivate:
                await self.session_crud.deactivate_session(db, session.id)
                logger.info(f"Deactivated excess session {session.id} for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up excess sessions: {e}")


class DeviceTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track device information and detect suspicious activity.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.session_crud = CRUDUserSession()
    
    async def dispatch(self, request: Request, call_next):
        """Track device information for authenticated requests."""
        
        # Get device information from headers
        user_agent = request.headers.get("User-Agent", "")
        device_fingerprint = request.headers.get("X-Device-Fingerprint", "")
        client_ip = self.get_client_ip(request)
        
        # Store device info in request state
        request.state.device_info = {
            "user_agent": user_agent,
            "device_fingerprint": device_fingerprint,
            "ip_address": client_ip
        }
        
        response = await call_next(request)
        
        # Update session device info if session exists
        if hasattr(request.state, "session_id"):
            try:
                db = next(get_db())
                await self.session_crud.update_device_info(
                    db,
                    request.state.session_id,
                    user_agent,
                    client_ip,
                    device_fingerprint
                )
            except Exception as e:
                logger.error(f"Error updating device info: {e}")
        
        return response
    
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # CSP header for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "script-src 'none'; "
                "style-src 'none'; "
                "img-src 'none'; "
                "connect-src 'self'; "
                "font-src 'none'; "
                "object-src 'none'; "
                "media-src 'none'; "
                "frame-src 'none';"
            )
        
        return response
