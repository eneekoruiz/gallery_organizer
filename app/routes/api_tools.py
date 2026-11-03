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
