from flask import Blueprint, jsonify, request, Response, send_file
from app.services.file_service import *
from app.services.face_service import api_scan_video

api_tools_bp = Blueprint('api_tools', __name__)

@api_tools_bp.route('/duplicates', methods=['POST'])
def api_duplicates_route():
    return api_duplicates()

@api_tools_bp.route('/purge_exact_duplicates', methods=['POST'])
@api_tools_bp.route('/purge_duplicates', methods=['POST'])
def api_purge_exact_duplicates_route():
    return api_purge_exact_duplicates()

@api_tools_bp.route('/recluster_unknowns', methods=['POST'])
def start_recluster_endpoint_route():
    return start_recluster_endpoint()

@api_tools_bp.route('/start_smart_clean', methods=['POST'])
def start_smart_clean_endpoint_route():
    return start_smart_clean_endpoint()

@api_tools_bp.route('/smart_clean_status')
def get_smart_clean_status_route():
    return get_smart_clean_status()

@api_tools_bp.route('/pending_sorted')
def api_pending_sorted_route():
    return api_pending_sorted()

@api_tools_bp.route('/mass_cleanup', methods=['POST'])
@api_tools_bp.route('/cleanup_mass', methods=['POST'])
def api_mass_cleanup_route():
    return api_mass_cleanup()

@api_tools_bp.route('/duplicates_scan')
def api_duplicates_scan_route():
    return api_duplicates_scan()

@api_tools_bp.route('/duplicates_clean', methods=['POST'])
def api_duplicates_clean_route():
    return api_duplicates_clean()

@api_tools_bp.route('/events')
def api_events_route():
    return api_events()

@api_tools_bp.route('/create_event_folder', methods=['POST'])
def api_create_event_folder_route():
    return api_create_event_folder()

@api_tools_bp.route('/similar_scan')
def api_similar_scan_route():
    return api_similar_scan()

@api_tools_bp.route('/similar_clean', methods=['POST'])
def api_similar_clean_route():
    return api_similar_clean()

@api_tools_bp.route('/sharpness')
def api_sharpness_route():
    return api_sharpness()

@api_tools_bp.route('/scan_video', methods=['POST'])
def api_scan_video_route():
    return api_scan_video()

@api_tools_bp.route('/clear_cache', methods=['POST'])
def api_clear_cache_route():
    return api_clear_cache()
@api_tools_bp.route('/triage/status')
def api_triage_status_route():
    import json
    from app.globals import APP_DIR
    status_file = APP_DIR / "scripts" / "triage_status.json"
    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as sf:
                return jsonify(json.load(sf))
        except Exception as e:
            return jsonify({'status': 'reading', 'error': str(e)})
    return jsonify({'status': 'idle'})

@api_tools_bp.route('/icloud/start', methods=['POST'])
def api_icloud_start_route():
    from app.services.icloud_sync_service import start_icloud_sync
    return jsonify(start_icloud_sync())

@api_tools_bp.route('/icloud/stop', methods=['POST'])
def api_icloud_stop_route():
    from app.services.icloud_sync_service import stop_icloud_sync
    return jsonify(stop_icloud_sync())

@api_tools_bp.route('/icloud/status')
def api_icloud_status_route():
    from app.services.icloud_sync_service import get_icloud_sync_status
    return jsonify(get_icloud_sync_status())


@api_tools_bp.route('/supervisor/status')
def api_supervisor_status_route():
    from app.services.supervisor_service import get_supervisor_status
    return jsonify(get_supervisor_status())

@api_tools_bp.route('/supervisor/audit_now', methods=['POST'])
def api_supervisor_audit_now_route():
    from app.services.supervisor_service import audit_recent_decisions
    data = request.json or {}
    n = data.get('n', 30)
    return jsonify(audit_recent_decisions(n=n))

@api_tools_bp.route('/gallery/pending_status')
def api_gallery_pending_status_route():
    from app.globals import APP_DIR
    import json
    prog_file = APP_DIR / "scratch" / "apple_progress.json"
    pending_count = 0
    if prog_file.exists():
        try:
            with open(prog_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                pending_count = d.get("pending_analysis_videos", 0)
        except Exception:
            pass
    return jsonify({
        "pending_videos": pending_count,
        "success": True
    })

@api_tools_bp.route('/media/analyze_video', methods=['POST'])
def api_media_analyze_video_route():
    import json, os, subprocess, time
    from pathlib import Path
    from app.globals import APP_DIR, clear_gallery_cache
    from app.services.face_service import api_scan_video
    
    data = request.json or {}
    filepath = data.get('path', '')
    
    # 1. Resolver si es un acceso directo .url
    if filepath.endswith('.url') and os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as uf:
                for line in uf:
                    if line.startswith('URL=file:///'):
                        filepath = line.replace('URL=file:///', '').strip().replace('/', '\\')
                        break
        except Exception:
            pass

    # 2. Si es archivo de iCloud, hidratar bajo demanda
    is_icloud = 'iCloud Photos' in filepath
    if is_icloud and os.path.exists(filepath):
        try:
            subprocess.run(["attrib", "-U", "+P", filepath], capture_output=True, timeout=5)
            for _ in range(6):
                try:
                    with open(filepath, "rb") as vf:
                        vf.read(1024)
                    break
                except OSError:
                    time.sleep(0.5)
        except Exception:
            pass

    # 3. Invocar escaneo de video
    if request.json:
        request.json['path'] = filepath
        request.json['force'] = True
    scan_res = api_scan_video()
    res_data = scan_res.get_json() if hasattr(scan_res, 'get_json') else (scan_res[0].get_json() if isinstance(scan_res, tuple) else {})
    
    # 4. Actualizar apple_db.json
    apple_db_path = APP_DIR / "apple_db.json"
    norm_fp = os.path.normpath(filepath)
    if apple_db_path.exists():
        try:
            with open(apple_db_path, "r", encoding="utf-8") as f:
                adb = json.load(f)
            
            target_key = None
            for k in adb.keys():
                if os.path.normcase(os.path.normpath(k)) == os.path.normcase(norm_fp):
                    target_key = k
                    break
            
            if target_key:
                adb[target_key]["needs_face_analysis"] = False
                adb[target_key]["status"] = "Analizado"
                if isinstance(res_data, dict) and res_data.get("detections"):
                    adb[target_key]["faces"] = res_data["detections"]
                
                temp_p = APP_DIR / "apple_db.json.tmp"
                with open(temp_p, "w", encoding="utf-8") as f:
                    json.dump(adb, f, indent=2, ensure_ascii=False)
                os.replace(temp_p, apple_db_path)
        except Exception as e:
            print(f"[ANALYZE_VIDEO] Error actualizando apple_db: {e}")

    # 5. Decrementar contador de videos pendientes
    prog_file = APP_DIR / "scratch" / "apple_progress.json"
    pending_left = 0
    if prog_file.exists():
        try:
            with open(prog_file, "r", encoding="utf-8") as f:
                pdata = json.load(f)
            pdata["pending_analysis_videos"] = max(0, pdata.get("pending_analysis_videos", 1) - 1)
            pending_left = pdata["pending_analysis_videos"]
            with open(prog_file, "w", encoding="utf-8") as f:
                json.dump(pdata, f, indent=2)
        except Exception:
            pass

    # 6. Dehidratar de nuevo para liberar espacio en disco
    if is_icloud and os.path.exists(filepath):
        try:
            subprocess.run(["attrib", "+U", "-P", filepath], capture_output=True, timeout=5)
        except Exception:
            pass

    clear_gallery_cache()
    return jsonify({
        "success": True,
        "detections": res_data.get("detections") if isinstance(res_data, dict) else [],
        "pending_videos": pending_left
    })
