import sys

# 1. Patch app.py for HTTP Cache Headers & 280px fast WebP thumbnails
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Update generate_thumbnail default size to 280
if "max_size=400" in app_code:
    app_code = app_code.replace("max_size=400", "max_size=280")
    print("Updated thumbnail max_size to 280px for ultra-fast loading")

# Update api_thumbnail with Cache-Control headers
old_api_thumb = """@app.route('/api/thumbnail')
def api_thumbnail():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    filepath = real_path
    
    thumb = generate_thumbnail(filepath)
    if thumb and os.path.exists(thumb):
        return send_file(thumb, mimetype='image/webp')
    
    # Fallback to original
    if os.path.exists(filepath):
        return send_file(filepath)
    return "No encontrado", 404"""

new_api_thumb = """@app.route('/api/thumbnail')
def api_thumbnail():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    filepath = real_path
    
    thumb = generate_thumbnail(filepath)
    if thumb and os.path.exists(thumb):
        res = send_file(thumb, mimetype='image/webp')
        res.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return res
    
    # Fallback to original
    if os.path.exists(filepath):
        res = send_file(filepath)
        res.headers['Cache-Control'] = 'public, max-age=86400'
        return res
    return "No encontrado", 404"""

if old_api_thumb in app_code:
    app_code = app_code.replace(old_api_thumb, new_api_thumb)
    print("Patched api_thumbnail with HTTP Cache-Control headers")

# Update get_media with Cache-Control headers
old_get_media = """@app.route('/media')
def get_media():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    return send_file(real_path, conditional=True)"""

new_get_media = """@app.route('/media')
def get_media():
    filepath = request.args.get('path')
    real_path = find_relocated_file(filepath)
    if not real_path:
        return "Not found", 404
    res = send_file(real_path, conditional=True)
    res.headers['Cache-Control'] = 'public, max-age=86400'
    return res"""

if old_get_media in app_code:
    app_code = app_code.replace(old_get_media, new_get_media)
    print("Patched get_media with Cache-Control headers")

# Update api_person_avatar with Cache-Control headers
old_avatar_res = "return Response(buf.tobytes(), mimetype='image/jpeg')"
new_avatar_res = "res = Response(buf.tobytes(), mimetype='image/jpeg')\n        res.headers['Cache-Control'] = 'public, max-age=86400'\n        return res"

if old_avatar_res in app_code:
    app_code = app_code.replace(old_avatar_res, new_avatar_res)
    print("Patched api_person_avatar with Cache-Control headers")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

# 2. Patch templates/index.html for lazy loading & Lightbox preloading
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_code = f.read()

# Add loading="lazy" and decoding="async" to grid thumbnails
old_grid_img = '<img src="${thumbUrl}" alt="Photo" class="grid-thumb">'
new_grid_img = '<img src="${thumbUrl}" alt="Photo" class="grid-thumb" loading="lazy" decoding="async">'

if old_grid_img in html_code:
    html_code = html_code.replace(old_grid_img, new_grid_img)
    print("Added loading='lazy' decoding='async' to grid images in index.html")

# Add Lightbox image preloader
old_open_lb = "function openLightbox(fileObj) {"
new_open_lb = """function preloadAdjacentImages() {
    if (!currentGallery || currentGallery.length === 0) return;
    const nextIdx = (currentGalleryIndex + 1) % currentGallery.length;
    const prevIdx = (currentGalleryIndex - 1 + currentGallery.length) % currentGallery.length;
    if (currentGallery[nextIdx] && currentGallery[nextIdx].path) {
        const imgNext = new Image();
        imgNext.src = `/media?path=${encodeURIComponent(currentGallery[nextIdx].path)}`;
    }
    if (currentGallery[prevIdx] && currentGallery[prevIdx].path) {
        const imgPrev = new Image();
        imgPrev.src = `/media?path=${encodeURIComponent(currentGallery[prevIdx].path)}`;
    }
}

function openLightbox(fileObj) {"""

if old_open_lb in html_code:
    html_code = html_code.replace(old_open_lb, new_open_lb)
    print("Added preloadAdjacentImages to index.html")

# Trigger preload in openLightbox
if "preloadAdjacentImages();" not in html_code:
    html_code = html_code.replace("lbModal.classList.add('active');", "lbModal.classList.add('active');\n        preloadAdjacentImages();")
    print("Triggered preloadAdjacentImages in openLightbox")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)
