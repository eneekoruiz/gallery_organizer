import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

# 1. Update app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

magic_routes = """
import magic_links

@app.route('/share/<token>')
def view_share_guest(token):
    info = magic_links.get_magic_link_info(token)
    if not info:
        return render_template('share_guest.html', error="Enlace caducado o no válido")
    return render_template('share_guest.html')

@app.route('/api/share/<token>/gallery')
def api_share_guest_gallery(token):
    info = magic_links.get_magic_link_info(token)
    if not info:
        return jsonify({"error": "Enlace no válido"}), 404
        
    category = info['category']
    identity = info['identity']
    
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    items = []
    if category in _GALLERY_CACHE and identity in _GALLERY_CACHE[category]:
        items = _GALLERY_CACHE[category][identity]
        
    return jsonify({
        "category": category,
        "identity": identity,
        "items": items
    })

@app.route('/api/magic_links/create', methods=['POST'])
def api_create_magic_link():
    data = request.json or {}
    category = data.get('category')
    identity = data.get('identity')
    days = data.get('days')
    
    if not category or not identity:
        return jsonify({"error": "Faltan datos"}), 400
        
    token = magic_links.create_magic_link(category, identity, duration_days=days)
    share_url = f"{request.host_url}share/{token}"
    return jsonify({"success": True, "token": token, "share_url": share_url})

@app.route('/api/magic_links/list')
def api_list_magic_links():
    return jsonify({"links": magic_links.list_active_magic_links()})

@app.route('/api/magic_links/revoke', methods=['POST'])
def api_revoke_magic_link():
    data = request.json or {}
    token = data.get('token')
    if token and magic_links.revoke_magic_link(token):
        return jsonify({"success": True})
    return jsonify({"error": "Token no encontrado"}), 404
"""

if "import magic_links" not in app_code:
    pos = app_code.find("if __name__ == '__main__':")
    if pos != -1:
        app_code = app_code[:pos] + magic_routes + "\n" + app_code[pos:]

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("✓ Inyectadas rutas de Magic Share Links en app.py!")

# 2. Add button in templates/index.html sidebar
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

magic_btn_js = """
function generateMagicShareLink(category, identity) {
    fetch('/api/magic_links/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({category: category, identity: identity, days: 30})
    })
    .then(r => r.json())
    .then(data => {
        if (data.share_url) {
            navigator.clipboard.writeText(data.share_url);
            alert("🔗 ¡Enlace Mágico Copiado al Portapapeles!\\n\\nEnvíaselo a tu amigo para que vea sus fotos:\\n" + data.share_url);
        }
    });
}
window.generateMagicShareLink = generateMagicShareLink;
"""

if "window.generateMagicShareLink" not in html:
    pos_s = html.rfind('</script>')
    if pos_s != -1:
        html = html[:pos_s] + magic_btn_js + "\n" + html[pos_s:]
        with open('templates/index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ Inyectado controlador generateMagicShareLink en templates/index.html!")
