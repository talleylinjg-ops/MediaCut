import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models
from app.api import admin, ai, audio, dev, image, pay, result, tasks
from app.core import billing
from app.core.security import hash_api_key
from app.database import Base, SessionLocal, engine

API_KEY_PATHS = ("/api/v1/image", "/api/v1/audio", "/api/v1/ai", "/api/v1/tasks", "/api/v1/result")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
FRONTEND_DIST = os.path.normpath(os.path.join(BASE_DIR, "..", "frontend", "dist"))

SPA_EXCLUDED_PREFIXES = ("/api/", "/docs", "/redoc", "/openapi.json", "/static", "/health")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="媒体剪辑 API 服务平台",
    description="对外提供图片剪辑、音频剪辑与 ModelScope AI 能力的开放 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(404)
async def spa_fallback(request: Request, exc: HTTPException):
    if request.url.path.startswith(SPA_EXCLUDED_PREFIXES):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    index_file = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.get("/docs", include_in_schema=False)
async def custom_docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="媒体剪辑 API 服务平台 - Swagger UI",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/swagger/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    from fastapi.openapi.docs import get_redoc_html

    return get_redoc_html(openapi_url="/openapi.json", title="媒体剪辑 API 服务平台 - ReDoc")


@app.middleware("http")
async def usage_logging(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(API_KEY_PATHS):
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            db = SessionLocal()
            try:
                developer = db.query(models.Developer).filter(
                    models.Developer.api_key_hash == hash_api_key(auth[7:].strip())
                ).first()
                if developer is not None:
                    db.add(models.ApiCallLog(
                        developer_id=developer.id,
                        endpoint=request.url.path,
                        status_code=response.status_code,
                        cost=billing.get_price(request.url.path),
                    ))
                    db.commit()
            finally:
                db.close()
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(dev.router)
app.include_router(image.router)
app.include_router(audio.router)
app.include_router(ai.router)
app.include_router(tasks.router)
app.include_router(result.router)
app.include_router(admin.router)
app.include_router(pay.router)
