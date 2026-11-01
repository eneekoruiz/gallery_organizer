from flask import Blueprint, jsonify, request, Response, send_file
from app.services.gallery_service import *

api_gallery_bp = Blueprint('api_gallery', __name__)

@api_gallery_bp.route('/identities')
def api_identities_route():
    return api_identities()

@api_gallery_bp.route('/gallery')
def get_gallery_route():
    return get_gallery()

@api_gallery_bp.route('/gallery/refresh', methods=['GET', 'POST'])
def refresh_gallery_route():
    from app.globals import clear_gallery_cache
    clear_gallery_cache()
    return jsonify({"success": True, "message": "Gallery cache refreshed"})

@api_gallery_bp.route('/gallery/structure')
def get_gallery_structure_route():
    """Return only category/identity names with counts — no item data.
    Ultra-lightweight (~5KB) for instant sidebar rendering."""
    from app.globals import get_gallery_cache
    cache = get_gallery_cache()
    if cache is None:
        return jsonify({})
    structure = {}
    for cat, idents in cache.items():
        if cat == '__smart_album__':
            continue
        structure[cat] = {}
        for ident, items in idents.items():
            structure[cat][ident] = len(items) if isinstance(items, list) else 0
    return jsonify(structure)

@api_gallery_bp.route('/gallery/items')
def get_gallery_items_route():
    """Paginated items endpoint. Returns a slice of items for a specific cat/ident.
    Query params: cat, ident, offset (default 0), limit (default 60)"""
    from app.globals import get_gallery_cache
    cat = request.args.get('cat', '')
    ident = request.args.get('ident', '')
    offset = int(request.args.get('offset', 0))
    limit = min(int(request.args.get('limit', 60)), 200)

    cache = get_gallery_cache()
    if not cache or cat not in cache or ident not in cache[cat]:
        return jsonify({"items": [], "total": 0, "has_more": False})

    all_items = cache[cat][ident]
    total = len(all_items)
    page = all_items[offset:offset + limit]
    has_more = (offset + limit) < total

    return jsonify({
        "items": page,
        "total": total,
        "offset": offset,
        "has_more": has_more
    })

@api_gallery_bp.route('/gallery/progress')
def get_gallery_progress_route():
    from app.globals import get_gallery_scan_progress
    return jsonify({"progress": get_gallery_scan_progress()})

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

@api_gallery_bp.route('/face_top_matches', methods=['POST'])
def api_face_top_matches_route():
    from app.services.similarity_service import api_face_top_matches
    return api_face_top_matches()

@api_gallery_bp.route('/export/zip', methods=['GET', 'POST'])
def api_export_zip_route():
    return api_export_zip()

@api_gallery_bp.route('/events/timeline')
def api_events_timeline_route():
    return api_events_timeline()
