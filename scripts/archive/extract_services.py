import re
import os

def create_service(file_in, file_out, bp_name):
    with open(file_in, 'r', encoding='utf-8') as f:
        code = f.read()

    # Create service code
    service = code
    service = re.sub(r'from flask import Blueprint.*?send_file\n', '', service)
    service = re.sub(r'from flask import.*?\n', '', service)
    service = re.sub(fr"{bp_name} = Blueprint\(.*?\)\n", '', service)
    service = re.sub(fr"@{bp_name}\.route\(.*?\)\n", '', service)
    
    # Simple jsonify replacement
    # Just remove jsonify( and the closing parenthesis if it is on the same line
    service = re.sub(r'return jsonify\((.*?)\)(?=\n)', r'return \1', service)
    
    with open(file_out, 'w', encoding='utf-8') as f:
        f.write(service)

    # For the route code, we want it to be thin, but doing this via regex is hard.
    # So we'll leave this to manual replacement or simpler stub generation.

create_service('app/routes/api_gallery.py', 'app/services/gallery_service.py', 'api_gallery_bp')
create_service('app/routes/api_faces.py', 'app/services/face_service.py', 'api_faces_bp')
create_service('app/routes/api_tools.py', 'app/services/file_service.py', 'api_tools_bp')

print("Created service files.")
