"""Main application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from diting_web.api.v1 import router as v1_router
from diting_web.common.exceptions import DiTingWebException
from diting_web.common.logging import configure_logging, get_logger
from diting_web.common.response import error_response
from diting_web.config import settings
from diting_web.db.session import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting DiTing Web application", version=settings.app_version)

    # Configure logging
    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    # Initialize database (optional, use Alembic in production)
    if settings.environment == "development":
        logger.info("Initializing database tables")
        await init_db()

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down DiTing Web application")
    
    # Close ARQ client connection pool
    try:
        from diting_web.utils.arq_client import close_arq_client
        await close_arq_client()
        logger.info("ARQ client closed successfully")
    except Exception as e:
        logger.error("Failed to close ARQ client", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Web UI and API Gateway for LLM Evaluation Platform",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Exception handlers
@app.exception_handler(DiTingWebException)
async def diting_exception_handler(request: Request, exc: DiTingWebException) -> JSONResponse:
    """Handle DiTing custom exceptions."""
    logger.error(
        "DiTing exception occurred",
        error=exc.__class__.__name__,
        message=exc.message,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.code,
        content=error_response(
            error=exc.__class__.__name__,
            detail=exc.message,
            code=exc.code,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors."""
    # Filter out sensitive data from error details
    errors = exc.errors()
    
    # List of sensitive field names to mask
    sensitive_fields = {"password", "hashed_password", "api_key", "secret", "token", "refresh_token", "access_token"}
    
    # Clean errors to remove sensitive input data
    cleaned_errors = []
    for error in errors:
        error_copy = error.copy()
        # Check if the error location contains sensitive fields
        if "input" in error_copy and isinstance(error_copy["input"], dict):
            # Mask sensitive fields in input
            cleaned_input = {}
            for key, value in error_copy["input"].items():
                if key.lower() in sensitive_fields:
                    cleaned_input[key] = "***"
                else:
                    cleaned_input[key] = value
            error_copy["input"] = cleaned_input
        cleaned_errors.append(error_copy)
    
    logger.warning(
        "Validation error",
        errors=cleaned_errors,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            error="ValidationError",
            detail=str(cleaned_errors),
            code=422,
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        error=exc.__class__.__name__,
        message=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            error="InternalServerError",
            detail="An internal server error occurred" if not settings.debug else str(exc),
            code=500,
        ),
    )


# Include routers
app.include_router(v1_router)


# Root endpoint
@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "diting_web.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

