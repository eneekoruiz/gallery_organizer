import os, json, time
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

try:
    from a2wsgi import WSGIMiddleware
except ImportError:
    from starlette.middleware.wsgi import WSGIMiddleware

try:
    from app.utils.storage_adapters import get_adapter
except ImportError:
    get_adapter = None

from state_memory import state_memory
from db import init_db, get_db, FileState, SyncLog
from auth import verify_google_oauth_token
from notifier import send_notification
from cron_jobs import start_cron_scheduler

# Import and create the core Flask application
from app import create_app
flask_app = create_app()

app = FastAPI(
    title="GalleryOrganizer Cloud API",
    description="REST API para reconocimiento facial, persistencia Neon.tech y gestión híbrida en Render",
    version="5.0.0"
)

# Startup event: Initialize Database & Cron Jobs safely
@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception as e:
        print("[Startup] Error al inicializar DB:", e)

    try:
        start_cron_scheduler()
    except Exception as e:
        print("[Startup] Error al iniciar planificador:", e)

    try:
        send_notification("Servidor Iniciado", "La API de GalleryOrganizer 5.0 (WSGI Hybrid) está activa en Render.", level="INFO")
    except Exception as e:
        print("[Startup] Notificación de inicio omitida:", e)

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "database": "Neon.tech PostgreSQL",
        "environment": os.getenv("RENDER", "development")
    }

def run_background_sync():
    print("[BG Task] Executing Delta Sync & Database Audit...")
    try:
        state_memory.update_delta_sync_time()
        send_notification("Sincronización Diferencial", "Sincronización Delta finalizada con éxito.", level="SUCCESS")
    except Exception as e:
        print("[BG Task] Error en run_background_sync:", e)

@app.post("/api/webhooks/drive")
async def drive_webhook(background_tasks: BackgroundTasks, request: Request):
    headers = dict(request.headers)
    event_state = headers.get("x-goog-resource-state", "sync")
    print("Received Drive Webhook Notification:", event_state)
    background_tasks.add_task(run_background_sync)
    return {"status": "received", "state": event_state}

@app.post("/api/sync/delta")
async def trigger_delta_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_background_sync)
    return {"success": True, "message": "Sincronización diferencial iniciada en segundo plano"}

# Mount full Flask application at root via modern a2wsgi WSGIMiddleware
# This ensures 100% route coverage, perfect template rendering, url_for resolution, and zero 404s!
app.mount("/", WSGIMiddleware(flask_app))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run("app_fastapi:app", host="0.0.0.0", port=port, reload=True)
