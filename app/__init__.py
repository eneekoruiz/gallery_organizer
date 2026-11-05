from flask import Flask

from pathlib import Path
import os

def create_app(config=None):
    BASE_DIR = Path(__file__).resolve().parent.parent
    app = Flask(__name__, 
                template_folder=str(BASE_DIR / 'templates'),
                static_folder=str(BASE_DIR / 'static'))
    app.config.from_mapping(
        START_BACKGROUND_TASKS=os.getenv('SMART_GALLERY_BACKGROUND_TASKS', '1') == '1',
        AUTO_CLASSIFY=False,
        AUTO_START_ICLOUD=os.getenv("SMART_GALLERY_AUTO_START_ICLOUD", "0") == "1",
    )
    if config:
        app.config.update(config)
    background_enabled = app.config['START_BACKGROUND_TASKS'] and not app.testing


    
    # Import Blueprints
    from app.routes.views import views_bp
    from app.routes.api_gallery import api_gallery_bp
    from app.routes.api_faces import api_faces_bp
    from app.routes.api_tools import api_tools_bp
    from app.routes.api_sharing import api_sharing_bp
    from app.routes.api_events import api_events_bp
    from app.routes.api_config import api_config_bp
    
    # Register Blueprints
    app.register_blueprint(views_bp)
    app.register_blueprint(api_gallery_bp, url_prefix='/api')
    app.register_blueprint(api_faces_bp, url_prefix='/api')
    app.register_blueprint(api_tools_bp, url_prefix='/api')
    app.register_blueprint(api_sharing_bp)
    app.register_blueprint(api_events_bp)
    app.register_blueprint(api_config_bp)

    import gzip
    from flask import request

    @app.after_request
    def compress_response(response):
        if getattr(response, 'direct_passthrough', False):
            return response
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if ('gzip' in accept_encoding and 
            response.status_code == 200 and 
            'Content-Encoding' not in response.headers and
            response.mimetype in {'application/json', 'text/html', 'text/css', 'application/javascript'}):
            try:
                data = response.get_data()
                if len(data) > 1024:
                    compressed = gzip.compress(data, compresslevel=6)
                    response.set_data(compressed)
                    response.headers['Content-Encoding'] = 'gzip'
                    response.headers['Content-Length'] = len(compressed)
            except Exception:
                pass
        return response
    
    # Iniciar pre-generador de miniaturas en segundo plano (Modo Eco / No saturación)
    def start_bg_thumbnail_pregenerator():
        import threading
        import time
        import os
        import hashlib
        
        def run():
            # Espera 10s para dejar que el usuario abra la app y navegue con fluidez total
            time.sleep(10)
            try:
                from app.globals import FOTOS_DIR, RESULTADOS_DIR, THUMBNAILS_DIR
                from app.utils.files import generate_thumbnail
                
                valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
                all_files = []
                
                for scan_dir in [FOTOS_DIR, RESULTADOS_DIR]:
                    if not scan_dir.exists():
                        continue
                    for root, dirs, files in os.walk(str(scan_dir)):
                        for f in files:
                            p = Path(root) / f
                            if p.suffix.lower() in valid_exts:
                                all_files.append(p)
                
                pregen_count = 0
                for p in all_files:
                    try:
                        path_str = str(p)
                        path_hash = hashlib.md5(path_str.encode('utf-8')).hexdigest()
                        thumb_path = THUMBNAILS_DIR / f"{path_hash}.webp"
                        
                        if not thumb_path.exists():
                            generate_thumbnail(p)
                            pregen_count += 1
                            # Pausa suave de 40ms entre miniaturas para CPU < 5% y 0% saturación
                            time.sleep(0.04)
                    except Exception:
                        pass
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()

    if background_enabled:
        start_bg_thumbnail_pregenerator()
    
    # Iniciar motor de auto-corrección persistente en segundo plano (Modo Eco)
    def start_bg_auto_correction():
        import threading
        import time
        def run_engine():
            # Espera 15s para permitir que la interfaz cargue al 100% de velocidad
            time.sleep(15)
            try:
                from app.services.face_service import start_background_engine_daemon
                start_background_engine_daemon()
            except Exception as e:
                print(f"[BOOT] Error iniciando motor de auto-corrección: {e}")
        threading.Thread(target=run_engine, daemon=True).start()

    # Classification changes user files; enable only after reviewing calibration.
    if background_enabled and app.config['AUTO_CLASSIFY']:
        start_bg_auto_correction()
    
    if background_enabled and app.config["AUTO_START_ICLOUD"]:
        from app.services.icloud_sync_service import start_icloud_sync
        start_icloud_sync()

    return app

