from flask import Blueprint, render_template, request, send_file
import os
import urllib.parse
from app.utils.files import find_relocated_file
from app.services.gallery_service import get_gallery_cache, get_gallery

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    return render_template('index.html')

@views_bp.route('/share')
def share_album_view():
    cat = request.args.get('cat', '')
    ident = request.args.get('ident', '')
    if not cat or not ident:
        return "Álbum no especificado", 404
        
    g_cache = get_gallery_cache()
    if g_cache is None:
        get_gallery()
        g_cache = get_gallery_cache() or {}
        
    items = g_cache.get(cat, {}).get(ident, [])
    clean_title = ident.replace('C. ', '').replace('F. ', '').replace('P. ', '').replace('M. ', '')
    avatar_url = f"/api/person_avatar?cat={urllib.parse.quote(cat)}&ident={urllib.parse.quote(ident)}"
    
    return render_template('share.html', title=clean_title, category=cat, identity=ident, photos=items, avatar_url=avatar_url)

@views_bp.route('/favicon.ico')
def favicon():
    return '', 204

@views_bp.after_request
def add_header(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

@views_bp.route('/media')
@views_bp.route('/api/media')
def get_media():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    res = send_file(real_path, conditional=True)
    res.headers['Cache-Control'] = 'public, max-age=86400'
    return res
