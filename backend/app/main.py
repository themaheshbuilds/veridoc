import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import logger
from app.db.database import init_db
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("Initializing VERIDOC AI Sovereign Database schema...")
    await init_db()
    logger.info("VERIDOC AI Security Platform successfully initialized.")
    yield
    logger.info("Shutting down VERIDOC AI services.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=(
        "VERIDOC — Sovereign Document Forensics & Dual-Trust Verification Platform. "
        "AI-Based Fake Identity & Document Screening System. "
        "Compliant with Section 63, Bharatiya Sakshya Adhiniyam (BSA) 2023. "
        "Operates 100% offline on-device with zero commercial cloud API dependency."
    ),
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount frontend directory if available
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(frontend_dir):
    @app.get("/", include_in_schema=False)
    @app.get("/home", include_in_schema=False)
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/verifydocuments", include_in_schema=False)
    @app.get("/verify", include_in_schema=False)
    async def serve_verify():
        verify_path = os.path.join(frontend_dir, "verify.html")
        return FileResponse(verify_path if os.path.exists(verify_path) else os.path.join(frontend_dir, "index.html"))

    @app.get("/qr-reader", include_in_schema=False)
    @app.get("/qr", include_in_schema=False)
    async def serve_qr():
        qr_path = os.path.join(frontend_dir, "qr.html")
        return FileResponse(qr_path if os.path.exists(qr_path) else os.path.join(frontend_dir, "index.html"))

    @app.get("/verified-documents", include_in_schema=False)
    @app.get("/verified", include_in_schema=False)
    @app.get("/stats", include_in_schema=False)
    async def serve_verified():
        verified_path = os.path.join(frontend_dir, "verified.html")
        return FileResponse(verified_path if os.path.exists(verified_path) else os.path.join(frontend_dir, "index.html"))

    @app.get("/api-access", include_in_schema=False)
    @app.get("/api-portal", include_in_schema=False)
    @app.get("/api", include_in_schema=False)
    async def serve_api():
        api_path = os.path.join(frontend_dir, "api.html")
        return FileResponse(api_path if os.path.exists(api_path) else os.path.join(frontend_dir, "index.html"))

    @app.get("/verification-history", include_in_schema=False)
    @app.get("/history", include_in_schema=False)
    async def serve_history():
        history_path = os.path.join(frontend_dir, "history.html")
        return FileResponse(history_path if os.path.exists(history_path) else os.path.join(frontend_dir, "index.html"))

    @app.get("/styles.css", include_in_schema=False)
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "styles.css"), media_type="text/css")

    @app.get("/styles-v2-additions.css", include_in_schema=False)
    async def serve_css_v2():
        v2_css = os.path.join(frontend_dir, "styles-v2-additions.css")
        if os.path.exists(v2_css):
            return FileResponse(v2_css, media_type="text/css")
        from fastapi import Response
        return Response(status_code=404)

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "app.js"), media_type="application/javascript")

    @app.get("/favicon.ico", include_in_schema=False)
    @app.get("/favicon.svg", include_in_schema=False)
    async def serve_favicon():
        fav_path = os.path.join(frontend_dir, "favicon.svg")
        if os.path.exists(fav_path):
            return FileResponse(fav_path, media_type="image/svg+xml")
        from fastapi import Response
        return Response(status_code=204)

    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

