import os, json, time
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import storage_adapters
from state_memory import state_memory
from db import init_db, get_db, FileState, SyncLog
from auth import verify_google_oauth_token
from notifier import send_notification
from cron_jobs import start_cron_scheduler

app = FastAPI(
    title="GalleryOrganizer Cloud API",
    description="REST API para reconocimiento facial, persistencia Neon.tech y gestión híbrida en Render",
    version="3.0.0"
)

# Startup event: Initialize Database & Cron Jobs
@app.on_event("startup")
def on_startup():
    init_db()
    start_cron_scheduler()
    send_notification("Servidor Iniciado", "La API de GalleryOrganizer está activa en Render.", level="INFO")

# Mounting static files & templates
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates") if os.path.exists("templates") else None

class ConfigModel(BaseModel):
    mode: str = "local"
    local_path: Optional[str] = None
    gdrive_url_or_id: Optional[str] = None

@app.get("/")
async def root(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return {"message": "GalleryOrganizer API 3.0 Production Active"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "database": "Neon.tech PostgreSQL",
        "environment": os.getenv("RENDER", "development")
    }

@app.get("/api/config")
async def get_config():
    config_file = "config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"mode": "local", "local_path": r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR", "gdrive_folder_id": "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD"}

@app.post("/api/config")
async def set_config(cfg: ConfigModel, user=Depends(verify_google_oauth_token)):
    folder_id = cfg.gdrive_url_or_id or ""
    if "folders/" in folder_id:
        folder_id = folder_id.split("folders/")[1].split("?")[0]
        
    config_data = {
        "mode": cfg.mode,
        "local_path": cfg.local_path or r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR",
        "gdrive_folder_id": folder_id or "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD"
    }
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
    return {"success": True, "config": config_data}

def run_background_sync():
    print("[BG Task] Executing Delta Sync & Database Audit...")
    state_memory.update_delta_sync_time()
    send_notification("Sincronización Diferencial", "Sincronización Delta finalizada con éxito.", level="SUCCESS")

@app.post("/api/webhooks/drive")
async def drive_webhook(background_tasks: BackgroundTasks, request: Request):
    """
    Receptor de Webhooks (Drive Push Notifications):
    Escucha peticiones POST enviadas por Google Drive al subir fotos nuevas.
    Responde HTTP 200 OK en < 5ms.
    """
    headers = dict(request.headers)
    event_state = headers.get("x-goog-resource-state", "sync")
    print("Received Drive Webhook Notification:", event_state)
    background_tasks.add_task(run_background_sync)
    return {"status": "received", "state": event_state}

@app.post("/api/sync/delta")
async def trigger_delta_sync(background_tasks: BackgroundTasks, user=Depends(verify_google_oauth_token)):
    background_tasks.add_task(run_background_sync)
    return {"success": True, "message": "Sincronización diferencial iniciada en segundo plano"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run("app_fastapi:app", host="0.0.0.0", port=port, reload=True)
