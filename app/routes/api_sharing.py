from flask import Blueprint, jsonify, request, render_template, send_file
import os
try:
    import magic_links
except ImportError:
    magic_links = None
try:
    import elite_features
except ImportError:
    elite_features = None

from app.globals import get_gallery_cache, set_gallery_cache

api_sharing_bp = Blueprint('api_sharing', __name__)

@api_sharing_bp.route('/share/<token>')
def view_share_guest(token):
    if not magic_links:
        return "Magic links module missing", 500
    info = magic_links.get_magic_link_info(token)
    if not info:
        return render_template('share_guest.html', error="Enlace caducado o no válido")
    return render_template('share_guest.html')

@api_sharing_bp.route('/api/share/<token>/gallery')
def api_share_guest_gallery(token):
    if not magic_links:
        return "Magic links module missing", 500
    info = magic_links.get_magic_link_info(token)
    if not info:
        return jsonify({"error": "Enlace no válido"}), 404
        
    category = info['category']
    identity = info['identity']
    
    gallery_cache = get_gallery_cache()
    if gallery_cache is None:
        # Avoid circular import, fallback to empty
        gallery_cache = {}
        
    items = []
    if category in gallery_cache and identity in gallery_cache[category]:
        items = gallery_cache[category][identity]
        
    return jsonify({
        "category": category,
        "identity": identity,
        "items": items
    })

@api_sharing_bp.route('/api/magic_links/create', methods=['POST'])
def api_create_magic_link():
    if not magic_links:
        return "Magic links module missing", 500
    data = request.json or {}
    category = data.get('category')
    identity = data.get('identity')
    days = data.get('days')
    
    if not category or not identity:
        return jsonify({"error": "Faltan datos"}), 400
        
    token = magic_links.create_magic_link(category, identity, duration_days=days)
    share_url = f"{request.host_url}share/{token}"
    return jsonify({"success": True, "token": token, "share_url": share_url})

@api_sharing_bp.route('/api/magic_links/list')
def api_list_magic_links():
    if not magic_links:
        return jsonify({"links": []})
    return jsonify({"links": magic_links.list_active_magic_links()})

@api_sharing_bp.route('/api/magic_links/revoke', methods=['POST'])
def api_revoke_magic_link():
    if not magic_links:
        return "Magic links module missing", 500
    data = request.json or {}
    token = data.get('token')
    if token and magic_links.revoke_magic_link(token):
        return jsonify({"success": True})
    return jsonify({"error": "Token no encontrado"}), 404

@api_sharing_bp.route('/api/share/<token>/download_zip')
def api_share_download_zip(token):
    if not magic_links or not elite_features:
        return "Modules missing", 500
    info = magic_links.get_magic_link_info(token)
    if not info:
        return jsonify({"error": "Enlace no válido"}), 404
        
    category = info['category']
    identity = info['identity']
    
    gallery_cache = get_gallery_cache()
    if gallery_cache is None:
        gallery_cache = {}
        
    paths = []
    if category in gallery_cache and identity in gallery_cache[category]:
        paths = [it['path'] for it in gallery_cache[category][identity]]
        
    zip_stream = elite_features.create_zip_stream(paths)
    return send_file(
        zip_stream,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"Album_{identity}.zip"
    )
