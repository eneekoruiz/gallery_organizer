from flask import Blueprint, jsonify, request, Response, send_file
from app.services.file_service import *
from app.services.face_service import api_scan_video

api_tools_bp = Blueprint('api_tools', __name__)

@api_tools_bp.route('/duplicates', methods=['POST'])
def api_duplicates_route():
    return api_duplicates()

@api_tools_bp.route('/purge_exact_duplicates', methods=['POST'])
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



