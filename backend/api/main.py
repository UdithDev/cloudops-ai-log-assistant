from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db.session import init_db 
from .service.ml_inference import get_classifier
from .routes.analyze import router as analyze_router
from .routes.history import router as history_router

APP_NAME = "cloudps-ai-log-assitant"

def create_app() -> FastAPI:
    app=FastAPI(title=APP_NAME)


    #CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credintials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

        # Load ML model(if exists) into memory
        _ = get_classifier()

    @app.get("/api/health")
    def health() -> dict:
        clf=get_classifier()
        return {
            "status": "ok",
            "service":"APP_NAME",
            "ml_enabled": clf.enabled,
            "ml_loaded": clf.model.loaded,
        }
    
    app.include_router(analyze_router)
    app.include_router(history_router)

    return app

app= create_app()

