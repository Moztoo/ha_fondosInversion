"""Main FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.config import settings
from app.database import init_db
from app.models import ErrorPayload, StandardErrorResponse

# Logging configuration
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bbva_fondos")

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook: initialize database schema and WAL mode on startup."""
    logger.info("Initializing database: %s", settings.DATABASE_PATH)
    init_db()
    yield
    logger.info("Service shutting down cleanly.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Servicio de extracción, almacenamiento histórico y consulta de rendimientos "
        "de fondos de inversión BBVA México ('Anaquel del Día Actual')."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware (configurable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For Home Assistant local dashboards and external integrations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Home Assistant Ingress Middleware
@app.middleware("http")
async def handle_ha_ingress_path(request: Request, call_next):
    ingress_path = request.headers.get("x-ingress-path")
    if ingress_path:
        request.scope["root_path"] = ingress_path
    response = await call_next(request)
    return response

# Exception handlers for standard error envelope
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        payload = ErrorPayload(
            code=exc.detail["code"],
            message=exc.detail["message"],
        )
    else:
        payload = ErrorPayload(
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardErrorResponse(success=False, error=payload).model_dump(),
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    payload = ErrorPayload(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred.",
    )
    return JSONResponse(
        status_code=500,
        content=StandardErrorResponse(success=False, error=payload).model_dump(),
    )

# Static and Templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount API
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_view(request: Request):
    """Serve the interactive web dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
        },
    )

@app.get("/api/v1/contract", include_in_schema=False)
async def get_contract():
    """Return the raw OpenAPI 3.1 specification for external contract consumption."""
    return JSONResponse(content=app.openapi())
