"""
Main FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.gzip import GZipMiddleware

# Core imports
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.exceptions.custom_exceptions import (
    BusinessLogicException,
    SessionExpiredException,
    InsufficientPermissionsException,
    CompanyIsolationException
)

# Middleware imports
from app.middleware import (
    SessionControlMiddleware,
    DeviceTrackingMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    BurstRateLimitMiddleware
)

# API routes
from app.api.v1.endpoints import (
    auth,
    users,
    companies,
    suppliers,
    tenders,
    quotes,
    kanban
)

# WebSocket handlers
from app.websockets import (
    notification_handler,
    kanban_handler,
    chat_handler
)

# Services
from app.services.notification_service import NotificationService
from app.db.session import init_db
from app.db.migration_manager import initialize_databases
from app.api.api_v1.api import api_router

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")
    
    try:
        # Initialize databases
        db_status = await initialize_databases()
        logger.info(f"Database status: {db_status}")
        
        # Initialize notification service
        notification_service = NotificationService()
        await notification_service.initialize()
        logger.info("Notification service initialized")
        
        # Add any other startup tasks here
        
        logger.info("Application started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        # Cleanup tasks
        try:
            # Close database connections
            # Stop background tasks
            # Cleanup resources
            pass
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Application shutdown complete")


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Sistema de Automação de Licitações com IA",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add security middleware
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(DeviceTrackingMiddleware)
    app.add_middleware(SessionControlMiddleware, max_sessions_per_user=5)
    
    # Add rate limiting middleware
    app.add_middleware(BurstRateLimitMiddleware, burst_limit=50, burst_window=60)
    app.add_middleware(RateLimitMiddleware)
    
    # Add compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Add trusted host middleware for production
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Include API routers
    app.include_router(
        auth.router,
        prefix="/api/v1/auth",
        tags=["Authentication"]
    )
    
    app.include_router(
        users.router,
        prefix="/api/v1/users",
        tags=["Users"]
    )
    
    app.include_router(
        companies.router,
        prefix="/api/v1/companies",
        tags=["Companies"]
    )
    
    app.include_router(
        suppliers.router,
        prefix="/api/v1/suppliers",
        tags=["Suppliers"]
    )
    
    app.include_router(
        tenders.router,
        prefix="/api/v1/tenders",
        tags=["Tenders"]
    )
    
    app.include_router(
        quotes.router,
        prefix="/api/v1/quotes",
        tags=["Quotes"]
    )
    
    app.include_router(
        kanban.router,
        prefix="/api/v1/kanban",
        tags=["Kanban"]
    )
    
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Add WebSocket endpoints
    @app.websocket("/ws/notifications/{token}")
    async def websocket_notifications(websocket, token: str):
        """WebSocket endpoint for real-time notifications."""
        await notification_handler.handle_connection(websocket, token)
    
    @app.websocket("/ws/kanban/{board_id}/{token}")
    async def websocket_kanban(websocket, board_id: str, token: str):
        """WebSocket endpoint for real-time Kanban updates."""
        await kanban_handler.handle_connection(websocket, board_id, token)
    
    @app.websocket("/ws/chat/{room_id}/{token}")
    async def websocket_chat(websocket, room_id: str, token: str, room_type: str = "general"):
        """WebSocket endpoint for real-time chat."""
        await chat_handler.handle_connection(websocket, room_id, token, room_type)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from app.db.migration_manager import BackendMigrationManager
        
        manager = BackendMigrationManager()
        db_status = await manager.check_migration_status()
        
        return {
            "status": "healthy" if all(db_status.values()) else "degraded",
            "databases": db_status
        }
    
    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "status_code": exc.status_code,
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "errors": exc.errors(),
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    @app.exception_handler(BusinessLogicException)
    async def business_logic_exception_handler(request: Request, exc: BusinessLogicException):
        """Handle business logic errors."""
        logger.warning(f"Business logic error: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.warning(f"Authentication error: {exc.message}")
        return JSONResponse(
            status_code=401,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    @app.exception_handler(AuthorizationError)
    async def authorization_exception_handler(request: Request, exc: AuthorizationError):
        """Handle authorization errors."""
        logger.warning(f"Authorization error: {exc.message}")
        return JSONResponse(
            status_code=403,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handle custom validation errors."""
        logger.warning(f"Validation error: {exc.message}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "timestamp": NotificationService.get_current_timestamp()
            }
        )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests."""
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} "
            f"({process_time:.3f}s) {request.method} {request.url}"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    return app


# Create the FastAPI application instance
app = create_application()

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    import time
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG
    )
