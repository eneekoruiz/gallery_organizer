import re
import os

def process_file(orig_path, route_out_path, service_out_path, bp_name, service_module):
    with open(orig_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # 1. Create the service file
    # The service file will be exactly the original code, BUT without the Blueprint instantiation
    # and without the route decorators. It keeps all imports (flask, etc) so everything works.
    
    service_code = code
    service_code = re.sub(fr"{bp_name} = Blueprint\(['\"].*?['\"], __name__\)\n+", "", service_code)
    service_code = re.sub(fr"@{bp_name}\.route\(.*?\)\n", "", service_code)
    
    with open(service_out_path, 'w', encoding='utf-8') as f:
        f.write(service_code)
        
    # 2. Extract routes to create the thin controller
    # We need to find pairs of:
    # @bp.route('/path', methods=[...])
    # def function_name():
    
    pattern = fr"@{bp_name}\.route\((.*?)\)\n(?: *def (\w+)\((.*?)\):)"
    matches = re.findall(pattern, code)
    
    route_code = f"from flask import Blueprint, jsonify, request, Response, send_file\n"
    route_code += f"from {service_module} import *\n\n"
    route_code += f"{bp_name} = Blueprint('{bp_name.replace('_bp', '')}', __name__)\n\n"
    
    for route_args, func_name, func_args in matches:
        route_code += f"@{bp_name}.route({route_args})\n"
        route_code += f"def {func_name}_route({func_args}):\n"
        if func_args:
            # Need to pass arguments if there are any
            args_list = [a.strip() for a in func_args.split(',')]
            call_args = ", ".join([a.split('=')[0].strip() for a in args_list])
            route_code += f"    return {func_name}({call_args})\n\n"
        else:
            route_code += f"    return {func_name}()\n\n"

    with open(route_out_path, 'w', encoding='utf-8') as f:
        f.write(route_code)

process_file('app/routes/api_gallery.py', 'app/routes/api_gallery.py', 'app/services/gallery_service.py', 'api_gallery_bp', 'app.services.gallery_service')
process_file('app/routes/api_faces.py', 'app/routes/api_faces.py', 'app/services/face_service.py', 'api_faces_bp', 'app.services.face_service')
process_file('app/routes/api_tools.py', 'app/routes/api_tools.py', 'app/services/file_service.py', 'api_tools_bp', 'app.services.file_service')

print("Refactoring complete.")
