from flask import Blueprint, jsonify, request, Response, send_file
from app.services.gallery_service import *

api_gallery_bp = Blueprint('api_gallery', __name__)

@api_gallery_bp.route('/identities')
def api_identities_route():
    return api_identities()

@api_gallery_bp.route('/gallery')
def get_gallery_route():
    return get_gallery()

@api_gallery_bp.route('/metadata')
def api_metadata_route():
    return api_metadata()

@api_gallery_bp.route('/stats')
def api_stats_route():
    return api_stats()

@api_gallery_bp.route('/person_avatar')
def api_person_avatar_route():
    return api_person_avatar()

@api_gallery_bp.route('/thumbnail')
def api_thumbnail_route():
    return api_thumbnail()

@api_gallery_bp.route('/timeline')
def api_timeline_route():
    return api_timeline()

@api_gallery_bp.route('/person/evolution')
def api_person_evolution_route():
    return api_person_evolution()

@api_gallery_bp.route('/map/locations')
def api_map_locations_route():
    return api_map_locations()

@api_gallery_bp.route('/remove_from_folder', methods=['POST'])
def api_remove_from_folder_route():
    return api_remove_from_folder()

@api_gallery_bp.route('/delete', methods=['POST'])
def api_delete_route():
    return api_delete()

@api_gallery_bp.route('/delete_group', methods=['POST'])
def api_delete_group_route():
    return api_delete_group()

@api_gallery_bp.route('/batch_move', methods=['POST'])
def api_batch_move_route():
    return api_batch_move()

@api_gallery_bp.route('/search/semantic')
def api_search_semantic_route():
    return api_search_semantic()


