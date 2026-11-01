import re

# 1. Update index.html to store data.new_path to avoid 404 on subsequent corrections
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()
    
old_ui_correct = '''                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('Recuadro guardado. Actualizando galería...');
                        loadGallery();
                        if (isCurrentVideo) {
                            setTimeout(() => closeLightbox(), 500);
                        }
                    }
                });'''
new_ui_correct = '''                }).then(r => r.json()).then(data => {
                    if (data.success) {
                        showToast('Recuadro guardado. Actualizando galería...');
                        if (data.new_path) {
                            currentFileObj.path = data.new_path.replace(/\\\\/g, '/');
                        }
                        loadGallery();
                        if (isCurrentVideo) {
                            setTimeout(() => closeLightbox(), 500);
                        }
                    } else if (data.error) {
                        alert("Error: " + data.error);
                    }
                });'''
if old_ui_correct in html_content:
    html_content = html_content.replace(old_ui_correct, new_ui_correct)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Patched index.html with new_path logic")

# 2. Add /api/duplicates endpoint to app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

dup_endpoint = '''
@app.route('/api/duplicates', methods=['POST'])
def api_duplicates():
    try:
        data = request.json
        filepath = data.get('path')
        if not filepath or not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404
            
        # Calculate sharpness
        sharpness = "N/A"
        if not filepath.lower().endswith(('.mp4', '.mov', '.avi')):
            img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
                sharpness = round(laplacian_var, 1)
        
        return jsonify({
            "sharpness": sharpness,
            "duplicate": None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''
if 'def api_duplicates()' not in app_content:
    app_content += dup_endpoint
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched app.py with /api/duplicates endpoint")
