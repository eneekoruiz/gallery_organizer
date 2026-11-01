import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.gallery_service import get_gallery
from flask import Flask

app = Flask(__name__)
with app.test_request_context('/api/gallery?force=true'):
    resp = get_gallery()
    data = resp.get_json()

items = data.get('Conocidos', {}).get('C. Sergio Lacasa', [])
print(f"Total items in Conocidos > C. Sergio Lacasa: {len(items)}")
for i, it in enumerate(items):
    fn = it.get('filename')
    p = it.get('path')
    is_ai = it.get('is_ai')
    print(f"  [{i+1}] {fn} | Path: {p} | is_ai={is_ai}")
