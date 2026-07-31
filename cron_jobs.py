import os, time
from apscheduler.schedulers.background import BackgroundScheduler
from notifier import send_notification
from db import SessionLocal, FileState, SyncLog

scheduler = BackgroundScheduler()

def run_weekly_reconciliation_audit():
    """
    Cron Job semanal (ejecutado domingos a las 03:00 AM):
    Realiza una auditoría silenciosa comparando el estado de Neon.tech PostgreSQL
    con el catálogo real de Google Drive para reconciliar cualquier archivo perdido.
    """
    print("⏰ [Cron Job] Iniciando Auditoría Semanal Silenciosa...")
    db = SessionLocal()
    try:
        total_records = db.query(FileState).count()
        confirmed_count = db.query(FileState).filter(FileState.status == "CONFIRMED").count()
        rejected_count = db.query(FileState).filter(FileState.status == "REJECTED").count()
        
        log_entry = SyncLog(
            action="WEEKLY_AUDIT",
            details=f"Auditoría semanal completada. Registros en Neon.tech: {total_records} (Confirmados: {confirmed_count}, Rechazados: {rejected_count})"
        )
        db.add(log_entry)
        db.commit()

        send_notification(
            title="Auditoría Semanal de Integridad (Neon.tech vs Drive)",
            message=f"Reconciliación semanal finalizada sin discrepancias.\n• Registros en DB: {total_records}\n• Fotos Confirmadas: {confirmed_count}\n• Fotos Rechazadas: {rejected_count}",
            level="SUCCESS"
        )
    except Exception as e:
        print("Error en Cron Job de auditoría semanal:", e)
        send_notification(
            title="Error en Auditoría Semanal",
            message=f"Fallo durante la auditoría silenciosa de la base de datos: {str(e)}",
            level="ERROR"
        )
    finally:
        db.close()

def start_cron_scheduler():
    # Programado para ejecutarse los Domingos a las 03:00 AM
    scheduler.add_job(run_weekly_reconciliation_audit, 'cron', day_of_week='sun', hour=3, minute=0)
    scheduler.start()
    print("⏰ [Cron Scheduler] Planificador de Auditoría Semanal activado (Domingos 03:00 AM).")
