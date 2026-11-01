import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update face collection and add folder owner auto-inference
old_faces_append = """                    faces_data.append({
                        "x": x, "y": y, "width": w, "height": h,
                        "img_width": width, "img_height": height,
                        "identity": identity_name,
                        "confidence": confidence_str
                    })"""

new_faces_append = """                    faces_data.append({
                        "x": x, "y": y, "width": w, "height": h,
                        "img_width": width, "img_height": height,
                        "identity": identity_name,
                        "confidence": confidence_str,
                        "feature": feature[0] if ('feature' in locals() and feature is not None) else None
                    })"""

content = content.replace(old_faces_append, new_faces_append)

# Add folder owner auto-inference before return
old_return = """    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})
        
    return jsonify({"faces": faces_data, "timestamp": timestamp})"""

new_return = """    # Inferencia por Propietario de Carpeta
    folder_owner = Path(filepath).parent.name
    is_valid_owner = folder_owner not in ["_Dudosos", "Personas Sin Nombre", "Resultados", "Fotos", "Conocidos", "Ignorar"]
    
    if is_valid_owner and len(faces_data) > 0:
        owner_assigned = any(f["identity"] == folder_owner for f in faces_data)
        if not owner_assigned:
            best_idx = -1
            best_owner_score = -1.0
            owner_centroid = known_faces.get(folder_owner, {}).get('centroid')
            
            for idx, f in enumerate(faces_data):
                if f["identity"] == "Desconocido":
                    if owner_centroid is not None and f.get("feature") is not None:
                        score = get_cosine_similarity(f["feature"], owner_centroid)
                        if score > best_owner_score:
                            best_owner_score = score
                            best_idx = idx
                            
            if best_idx == -1:
                for idx, f in enumerate(faces_data):
                    if f["identity"] == "Desconocido":
                        best_idx = idx
                        break
                        
            if best_idx != -1:
                faces_data[best_idx]["identity"] = folder_owner
                faces_data[best_idx]["confidence"] = "✨ 100.0% (Propietario del Álbum)"
                
    # Limpiar features de la respuesta JSON
    for f in faces_data:
        if "feature" in f: del f["feature"]

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)})
        
    return jsonify({"faces": faces_data, "timestamp": timestamp})"""

content = content.replace(old_return, new_return)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado con inferencia automática por propietario de carpeta.")
