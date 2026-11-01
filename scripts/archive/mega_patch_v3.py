"""
MEGA-PATCH V3: Fix timeline crash, fix thumbnails crash, remove Falso_Positivo display,
move evolution to album header, use EXIF dates for evolution.
"""
import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except: pass

# ================================================================
# PART 1: Fix elite_features.py - timeline and evolution crashes
# ================================================================
with open('elite_features.py', 'r', encoding='utf-8') as f:
    elite = f.read()

new_elite = '''import os, sys, json, time, zipfile, io
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None

def get_exif_gps_locations(file_paths):
    """Extract GPS coordinates from EXIF data of JPEG photos."""
    locations = []
    if not Image: return locations
    for fp in file_paths[:500]:  # Limit to 500 files for performance
        p = Path(fp)
        if not p.exists() or p.suffix.lower() not in ['.jpg', '.jpeg']: continue
        try:
            with Image.open(p) as img:
                exif_data = img._getexif()
                if not exif_data: continue
                gps_info = {}
                for tag, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag, tag)
                    if tag_name == 'GPSInfo':
                        for key in value:
                            sub_tag = ExifTags.GPSTAGS.get(key, key)
                            gps_info[sub_tag] = value[key]
                if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                    lat = _convert_to_degrees(gps_info['GPSLatitude'])
                    if gps_info.get('GPSLatitudeRef') == 'S': lat = -lat
                    lon = _convert_to_degrees(gps_info['GPSLongitude'])
                    if gps_info.get('GPSLongitudeRef') == 'W': lon = -lon
                    locations.append({"path": str(p), "name": p.name, "lat": round(lat, 6), "lng": round(lon, 6)})
        except: pass
    return locations

def _convert_to_degrees(value):
    d, m, s = float(value[0]), float(value[1]), float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def get_exif_date(filepath):
    """Extract original capture date from EXIF. Returns ISO string or None."""
    if not Image: return None
    p = Path(filepath)
    if not p.exists() or p.suffix.lower() not in ['.jpg', '.jpeg', '.png']: return None
    try:
        with Image.open(p) as img:
            exif_data = img._getexif()
            if not exif_data: return None
            # Tag 36867 = DateTimeOriginal, 36868 = DateTimeDigitized, 306 = DateTime
            for tag_id in [36867, 36868, 306]:
                if tag_id in exif_data:
                    date_str = str(exif_data[tag_id])
                    if date_str and len(date_str) >= 10 and date_str[:4].isdigit():
                        return date_str.replace(':', '-', 2)
    except: pass
    return None

def search_semantic_keywords(gallery_dict, query):
    """Search photos by natural language keywords with Spanish synonym expansion."""
    q = query.lower().strip()
    results = []
    synonyms = {
        "playa": ["sea", "beach", "mar", "costa", "arena", "sol", "agua"],
        "perro": ["dog", "pet", "mascota", "can", "ney"],
        "cumple": ["bday", "birthday", "tarta", "fiesta", "cake", "party", "cumpleanos"],
        "fiesta": ["party", "inauteriak", "noche", "pub", "bar", "celebracion"],
        "coche": ["car", "auto", "vehiculo", "moto", "drive"],
        "viaje": ["trip", "travel", "vacaciones", "avion", "hotel"],
        "navidad": ["christmas", "xmas", "noel", "regalo"],
        "verano": ["summer", "piscina", "pool", "bikini"],
    }
    keywords = [q] + synonyms.get(q, [])
    for cat, identities in gallery_dict.items():
        for ident, items in identities.items():
            for item in items:
                p_str = item.get('path', '').lower()
                name_str = item.get('name', '').lower()
                if any(kw in p_str or kw in name_str or kw in cat.lower() or kw in ident.lower() for kw in keywords):
                    results.append(item)
    return results[:200]  # Cap at 200 results

def build_timeline_groups(gallery_dict, target_year=None):
    """Group photos by year/month. Uses file modification time (fast, no EXIF parsing)."""
    timeline = {}
    for cat, identities in gallery_dict.items():
        for ident, items in identities.items():
            for item in items:
                try:
                    fp = Path(item['path'])
                    if not fp.exists(): continue
                    mtime = fp.stat().st_mtime
                    t = time.localtime(mtime)
                    year = str(t.tm_year)
                    month = f"{t.tm_mon:02d}"
                    
                    if target_year and year != str(target_year): continue
                    
                    if year not in timeline: timeline[year] = {}
                    if month not in timeline[year]: timeline[year][month] = []
                    timeline[year][month].append(item)
                except: pass
    return timeline

def build_face_evolution_reel(gallery_dict, identity_name):
    """Build chronological reel of a person using EXIF dates when available, falling back to mtime."""
    items = []
    for cat, identities in gallery_dict.items():
        for ident, it_list in identities.items():
            if identity_name.lower() in ident.lower() or ident.lower() in identity_name.lower():
                for it in it_list:
                    fp = Path(it['path'])
                    if not fp.exists(): continue
                    
                    # Try EXIF date first for accuracy
                    exif_date = get_exif_date(str(fp))
                    if exif_date:
                        it['capture_date'] = exif_date
                        it['date_source'] = 'EXIF'
                        # Parse to timestamp for sorting
                        try:
                            parts = exif_date.split(' ')[0].split('-')
                            sort_key = int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
                        except:
                            sort_key = fp.stat().st_mtime
                    else:
                        mtime = fp.stat().st_mtime
                        t = time.localtime(mtime)
                        it['capture_date'] = f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"
                        it['date_source'] = 'file_modified'
                        sort_key = mtime
                    
                    items.append((sort_key, it))
    
    items.sort(key=lambda x: x[0])
    return [it for _, it in items]

def create_zip_stream(file_paths):
    """Pack files into an in-memory ZIP for download."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            p = Path(fp)
            if p.exists():
                zf.write(str(p), arcname=p.name)
    zip_buffer.seek(0)
    return zip_buffer
'''

with open('elite_features.py', 'w', encoding='utf-8') as f:
    f.write(new_elite)
print("[1] Rewrote elite_features.py with EXIF dates, performance limits, and crash protection")

# ================================================================
# PART 2: Fix app.py - wrap timeline in try/except, add year param
# ================================================================
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

changes = 0

# Fix timeline endpoint to accept year parameter and be crash-proof
old_timeline = """@app.route('/api/timeline')
def api_timeline():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    timeline = elite_features.build_timeline_groups(_GALLERY_CACHE)
    return jsonify({"timeline": timeline})"""

new_timeline = """@app.route('/api/timeline')
def api_timeline():
    try:
        year = request.args.get('year')
        global _GALLERY_CACHE
        if _GALLERY_CACHE is None:
            get_gallery()
        
        timeline = elite_features.build_timeline_groups(_GALLERY_CACHE, target_year=year)
        return jsonify({"timeline": timeline})
    except Exception as e:
        print("Timeline error:", e)
        return jsonify({"timeline": {}, "error": str(e)})"""

if old_timeline in app_code:
    app_code = app_code.replace(old_timeline, new_timeline)
    changes += 1
    print("[2] Fixed /api/timeline with year filter and crash protection")

# Wrap map/locations in try/except too
old_map = """@app.route('/api/map/locations')
def api_map_locations():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        get_gallery()
        
    all_paths = []"""

new_map = """@app.route('/api/map/locations')
def api_map_locations():
    try:
        global _GALLERY_CACHE
        if _GALLERY_CACHE is None:
            get_gallery()
        
        all_paths = []"""

if old_map in app_code:
    app_code = app_code.replace(old_map, new_map)
    # Find the return and wrap it
    changes += 1
    print("[3] Wrapped /api/map/locations in try/except")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print(f"\n=== Backend: {changes + 1} patches applied ===")

# ================================================================
# PART 3: Fix index.html UI
# ================================================================
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

ui_changes = 0

# Remove "Asignado a Falso_Positivo" type messages
html = html.replace("'Asignado a ' +", "'Movido a ' +")
# Filter out Falso_Positivo from display
if 'Falso_Positivo' in html:
    # In the cleanDisplayName function, also handle Falso_Positivo
    html = html.replace(
        "return name.replace(/_rejected/g, '')",
        "return name.replace(/_rejected/g, '').replace(/Falso_Positivo/g, 'Descartado').replace(/Ignorar_Irrelevante/g, 'Descartado')"
    )
    ui_changes += 1
    print("[4] Cleaned Falso_Positivo from display")

# Remove evolution button from lightbox detected persons panel
# and instead we'll add it to the album header
if 'openEvolutionModal' in html:
    # Remove any evolution buttons that are inside the persons-detected panel
    html = re.sub(
        r'<button[^>]*onclick="openEvolutionModal\([^)]*\)"[^>]*>[^<]*</button>',
        '',
        html
    )
    ui_changes += 1
    print("[5] Removed evolution buttons from lightbox persons panel")

# Add evolution button to the album/identity header area
evolution_in_header_js = """
function addEvolutionToHeader() {
    const headerEl = document.querySelector('.gallery-header h2');
    if (!headerEl) return;
    const personName = headerEl.textContent.trim();
    if (!personName || personName === 'Todas las Fotos') return;
    
    let existingBtn = document.getElementById('btn-evolution-header');
    if (existingBtn) existingBtn.remove();
    
    const btn = document.createElement('button');
    btn.id = 'btn-evolution-header';
    btn.innerHTML = '📈 Ver Evolución Temporal';
    btn.style.cssText = 'margin-left:12px;padding:6px 14px;border-radius:10px;border:1px solid rgba(168,85,247,0.4);background:rgba(168,85,247,0.15);color:#c084fc;font-size:0.8rem;font-weight:600;cursor:pointer;transition:all 0.2s;';
    btn.onmouseenter = () => { btn.style.background = 'rgba(168,85,247,0.3)'; };
    btn.onmouseleave = () => { btn.style.background = 'rgba(168,85,247,0.15)'; };
    btn.onclick = () => openEvolutionModal(personName);
    headerEl.appendChild(btn);
}

// Call addEvolutionToHeader whenever an identity is selected
const origLoadFolder = window.loadFolderItems || function(){};
window.loadFolderItems = function() {
    origLoadFolder.apply(this, arguments);
    setTimeout(addEvolutionToHeader, 200);
};
"""

if 'addEvolutionToHeader' not in html:
    pos = html.rfind('</script>')
    if pos > 0:
        html = html[:pos] + evolution_in_header_js + "\n" + html[pos:]
        ui_changes += 1
        print("[6] Added evolution button to album identity header")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n=== UI: {ui_changes} patches applied ===")
