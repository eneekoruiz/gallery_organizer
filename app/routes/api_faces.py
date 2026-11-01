from flask import Blueprint, jsonify, request, Response, send_file
from app.services.face_service import *
from app.services.task_service import api_task_status, api_task_list, api_task_retry

api_faces_bp = Blueprint('api_faces', __name__)

@api_faces_bp.route('/analyze', methods=['POST'])
def api_analyze_route():
    return api_analyze()

@api_faces_bp.route('/correct', methods=['POST'])
def api_correct_route():
    return api_correct()

@api_faces_bp.route('/undo_discard', methods=['POST'])
def api_undo_discard_route():
    return api_undo_discard()

@api_faces_bp.route('/rename_group', methods=['POST'])
def api_rename_group_route():
    return api_rename_group()

@api_faces_bp.route('/relearn_cascade', methods=['POST'])
def api_relearn_cascade_route():
    return api_relearn_cascade()

@api_faces_bp.route('/auto_classify_filename', methods=['POST'])
def api_auto_classify_filename_route():
    return api_auto_classify_filename()

@api_faces_bp.route('/reset_face_learning', methods=['POST'])
def api_reset_face_learning_route():
    return api_reset_face_learning()

@api_faces_bp.route('/rebuild_clean_centroids', methods=['POST'])
def api_rebuild_clean_centroids_route():
    return api_rebuild_clean_centroids()

@api_faces_bp.route('/detect_deep', methods=['POST'])
def api_detect_deep_route():
    return api_detect_deep()

@api_faces_bp.route('/correct_bulk', methods=['POST'])
def api_correct_bulk_route():
    return api_correct_bulk()

@api_faces_bp.route('/clear_confidence_cache', methods=['POST'])
def api_clear_confidence_cache_route():
    return api_clear_confidence_cache()

@api_faces_bp.route('/intensive_search_yo', methods=['POST'])
def api_intensive_search_yo_route():
    return api_intensive_search_yo()

@api_faces_bp.route('/yo_search_status')
def api_yo_search_status_route():
    return api_yo_search_status()

@api_faces_bp.route('/smart_audit', methods=['POST'])
def api_smart_audit_route():
    return api_smart_audit()

@api_faces_bp.route('/audit_status')
def api_audit_status_route():
    return api_audit_status()

# ── Task system routes ──────────────────────────────────────
@api_faces_bp.route('/task_status', methods=['GET'])
@api_faces_bp.route('/task_status/<task_id>', methods=['GET'])
def api_task_status_route(task_id=None):
    return api_task_status()

@api_faces_bp.route('/tasks', methods=['GET'])
def api_task_list_route():
    return api_task_list()

@api_faces_bp.route('/task_retry', methods=['POST'])
@api_faces_bp.route('/task_retry/<task_id>', methods=['POST'])
def api_task_retry_route(task_id=None):
    return api_task_retry()

@api_faces_bp.route('/auto_classify_continuous', methods=['POST'])
def auto_classify_route():
    return api_auto_classify_continuous()

@api_faces_bp.route('/self_audit_status', methods=['GET'])
def api_self_audit_status_route():
    return api_self_audit_status()

@api_faces_bp.route('/self_audit_stream', methods=['GET'])
def api_self_audit_stream_route():
    return api_self_audit_stream()

@api_faces_bp.route('/organize_quotes', methods=['POST'])
def api_organize_quotes_route():
    return api_organize_quotes()

@api_faces_bp.route('/suggest_merges', methods=['GET'])
def api_suggest_merges_route():
    return api_suggest_merges()

@api_faces_bp.route('/suggest_merges_execute', methods=['POST'])
def api_suggest_merges_execute_route():
    return api_suggest_merges_execute()




@api_faces_bp.route('/video_indexer/start', methods=['POST'])
def api_video_indexer_start_route():
    return api_video_indexer_start()

@api_faces_bp.route('/video_indexer/status', methods=['GET'])
def api_video_indexer_status_route():
    return api_video_indexer_status()

@api_faces_bp.route('/video_indexer/pause', methods=['POST'])
def api_video_indexer_pause_route():
    return api_video_indexer_pause()
