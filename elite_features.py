# -*- coding: utf-8 -*-
"""
elite_features.py
Provides EXIF GPS extraction with smart city/region geocoding fallback for places and events,
ensuring that all organized photos in Lugares/Eventos appear on the interactive map.
"""
import os, sys, json, time, math
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    Image = None

# Base de datos de coordenadas para carpetas conocidas de Lugares y Eventos
FOLDER_COORDINATES = {
    # Italia
    "florencia": (43.7696, 11.2558),
    "firenze": (43.7696, 11.2558),
    "burano": (45.4854, 12.4167),
    "venecia": (45.4408, 12.3155),
    "venezia": (45.4408, 12.3155),
    "roma": (41.9028, 12.4964),
    "milan": (45.4642, 9.1900),
    "italia": (43.7696, 11.2558), # Default Toscana / Florencia
    # País Vasco / España / Francia
    "irun": (43.3390, -1.7894),
    "bar de irun": (43.3390, -1.7894),
    "bilbao": (43.2630, -2.9350),
    "hendaia": (43.3592, -1.7744),
    "hendaye": (43.3592, -1.7744),
    "burgos": (42.3440, -3.6969),
    "biteri txiki": (43.3050, -1.9750),
    "donostia": (43.3183, -1.9812),
    "san sebastian": (43.3183, -1.9812),
    "casa nueva": (43.3390, -1.7894),
    "casas": (43.3390, -1.7894),
    "madrid": (40.4168, -3.7038),
    "barcelona": (41.3851, 2.1734),
    "paris": (48.8566, 2.3522),
    "londres": (51.5074, -0.1278),
    "london": (51.5074, -0.1278),
}

def get_exif_gps_locations(file_paths):
    """Extract GPS coordinates from EXIF data with fallback geocoding for place/event folders and disk cache."""
    locations = []
    cache_path = Path("file_gps_cache.json")
    cache_data = {}
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
        except Exception:
            pass
        
    cache_updated = False
    valid_exts = {'.jpg', '.jpeg', '.png', '.webp'}
    
    # Procesar hasta 1500 archivos para un mapa ultra rico
    for fp in file_paths[:1500]:
        p = Path(fp)
        if not p.exists() or p.suffix.lower() not in valid_exts:
            continue
        fpath_str = str(p)
        
        try:
            stat = p.stat()
            size = stat.st_size
            mtime = stat.st_mtime
            
            if fpath_str in cache_data and cache_data[fpath_str].get('size') == size and cache_data[fpath_str].get('mtime') == mtime:
                cached_loc = cache_data[fpath_str].get('loc')
                if cached_loc:
                    locations.append(cached_loc)
                continue
                
            loc_res = None
            
            # 1. Intentar EXIF Real si es JPG
            if Image and p.suffix.lower() in ['.jpg', '.jpeg']:
                try:
                    with Image.open(p) as img:
                        exif_data = img._getexif()
                        if exif_data:
                            gps_info = {}
                            for tag, value in exif_data.items():
                                tag_name = ExifTags.TAGS.get(tag, tag)
                                if tag_name == 'GPSInfo':
                                    for key in value:
                                        sub_tag = ExifTags.GPSTAGS.get(key, key)
                                        gps_info[sub_tag] = value[key]
                            if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                                lat = _convert_to_degrees(gps_info['GPSLatitude'])
                                lon = _convert_to_degrees(gps_info['GPSLongitude'])
                                if lat is not None and lon is not None:
                                    if gps_info.get('GPSLatitudeRef') == 'S': lat = -lat
                                    if gps_info.get('GPSLongitudeRef') == 'W': lon = -lon
                                    if not (math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon)):
                                        loc_res = {
                                            "path": fpath_str, 
                                            "name": p.name, 
                                            "lat": round(lat, 6), 
                                            "lng": round(lon, 6),
                                            "folder": p.parent.name,
                                            "source": "EXIF GPS"
                                        }
                except Exception:
                    pass

            # 2. Fallback inteligente: Coordenadas por Carpeta de Lugar/Evento
            if not loc_res:
                folder_lower = p.parent.name.lower().strip()
                parent_folder_lower = p.parent.parent.name.lower().strip() if len(p.parts) > 2 else ""
                
                matched_coords = None
                matched_label = folder_lower
                
                if folder_lower in FOLDER_COORDINATES:
                    matched_coords = FOLDER_COORDINATES[folder_lower]
                elif parent_folder_lower in FOLDER_COORDINATES:
                    matched_coords = FOLDER_COORDINATES[parent_folder_lower]
                    matched_label = parent_folder_lower
                else:
                    for k, coords in FOLDER_COORDINATES.items():
                        if k in folder_lower or k in parent_folder_lower:
                            matched_coords = coords
                            matched_label = k
                            break
                            
                if matched_coords:
                    # Añadir una variación minúscula aleatoria (jitter de 50 metros) para que los marcadores no se tapen exactamente
                    import random
                    lat_j = matched_coords[0] + random.uniform(-0.0005, 0.0005)
                    lng_j = matched_coords[1] + random.uniform(-0.0005, 0.0005)
                    loc_res = {
                        "path": fpath_str,
                        "name": p.name,
                        "lat": round(lat_j, 6),
                        "lng": round(lng_j, 6),
                        "folder": p.parent.name,
                        "source": f"Ubicación Álbum ({matched_label.title()})"
                    }
                    
            if loc_res:
                locations.append(loc_res)
                
            cache_data[fpath_str] = {'size': size, 'mtime': mtime, 'loc': loc_res}
            cache_updated = True
        except Exception:
            pass
            
    if cache_updated:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
        except Exception:
            pass
            
    return locations

def _convert_to_degrees(value):
    try:
        if isinstance(value, tuple) and len(value) == 3:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        return float(value)
    except Exception:
        return None
