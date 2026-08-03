from flask import Blueprint, jsonify, request, Response, send_file
from app.services.face_service import *

api_faces_bp = Blueprint('api_faces', __name__)

@api_faces_bp.route('/analyze', methods=['POST'])
def api_analyze_route():
    return api_analyze()

@api_faces_bp.route('/correct', methods=['POST'])
def api_correct_route():
    return api_correct()

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




