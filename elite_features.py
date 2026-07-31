import os, sys, json, time, zipfile, io
from pathlib import Path

# Try importing PIL EXIF reader for GPS extraction
try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None

def get_exif_gps_locations(file_paths):
    """
    6. Mapa Interactivo EXIF GPS:
    Extrae las coordenadas de geolocalización GPS (latitud, longitud) de las fotografías.
    """
    locations = []
    if not Image:
        return locations

    for fp in file_paths:
        p = Path(fp)
        if not p.exists() or p.suffix.lower() not in ['.jpg', '.jpeg']:
            continue
        try:
            with Image.open(p) as img:
                exif_data = img._getexif()
                if not exif_data:
                    continue
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

                    locations.append({
                        "path": str(p),
                        "name": p.name,
                        "lat": round(lat, 6),
                        "lng": round(lon, 6)
                    })
        except Exception:
            pass

    return locations

def _convert_to_degrees(value):
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def search_semantic_keywords(gallery_dict, query: str):
    """
    1. Búsqueda Semántica por Lenguaje Natural / Palabras Clave:
    Filtra fotos por conceptos ("playa", "perro", "gafas", "cumpleaños", "fiesta", etc.).
    """
    q = query.lower().strip()
    results = []

    synonyms = {
        "playa": ["sea", "beach", "mar", "costa", "arena", "sol", "agua"],
        "perro": ["dog", "pet", "mascota", "can", "ney"],
        "cumpleaños": ["bday", "birthday", "tarta", "fiesta", "cake", "party"],
        "fiesta": ["party", "inauteriak", "noche", "pub", "bar", "celebracion"],
        "coche": ["car", "auto", "vehiculo", "moto", "drive"]
    }
    keywords = [q] + synonyms.get(q, [])

    for cat, identities in gallery_dict.items():
        for ident, items in identities.items():
            for item in items:
                p_str = item.get('path', '').lower()
                name_str = item.get('name', '').lower()
                
                if any(kw in p_str or kw in name_str or kw in cat.lower() or kw in ident.lower() for kw in keywords):
                    results.append(item)

    return results

def build_timeline_groups(gallery_dict):
    """
    2. Máquina del Tiempo / Línea del Tiempo Interactiva:
    Agrupa fotos por Años y Meses a partir de fechas de modificación/captura.
    """
    timeline = {}
    for cat, identities in gallery_dict.items():
        for ident, items in identities.items():
            for item in items:
                fp = Path(item['path'])
                year = "2024"
                month = "01"
                try:
                    if fp.exists():
                        mtime = fp.stat().st_mtime
                        t_struct = time.localtime(mtime)
                        year = str(t_struct.tm_year)
                        month = f"{t_struct.tm_mon:02d}"
                except: pass

                if year not in timeline:
                    timeline[year] = {}
                if month not in timeline[year]:
                    timeline[year][month] = []

                timeline[year][month].append(item)

    return timeline

def build_face_evolution_reel(gallery_dict, identity_name: str):
    """
    5. Timelapse de Evolución del Rostro:
    Ordena cronológicamente todas las tomas registradas de una persona.
    """
    items = []
    for cat, identities in gallery_dict.items():
        for ident, it_list in identities.items():
            if identity_name.lower() in ident.lower() or ident.lower() in identity_name.lower():
                for it in it_list:
                    fp = Path(it['path'])
                    mtime = fp.stat().st_mtime if fp.exists() else 0
                    items.append((mtime, it))

    items.sort(key=lambda x: x[0])
    return [it for _, it in items]

def create_zip_stream(file_paths):
    """
    3. Generador de Archivo ZIP para Descarga en Bloque:
    Empaqueta los archivos de una galería compartida en un ZIP comprimido.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for fp in file_paths:
            p = Path(fp)
            if p.exists():
                zip_file.write(str(p), arcname=p.name)
    zip_buffer.seek(0)
    return zip_buffer
