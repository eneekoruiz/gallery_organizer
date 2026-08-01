import os, sys, json, time, zipfile, io
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
