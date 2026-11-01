import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

bad_snippet = """    except Exception as e:
        return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "Carpeta no encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

clean_snippet = """    except Exception as e:
        return jsonify({"error": str(e)}), 500"""

if bad_snippet in app_code:
    app_code = app_code.replace(bad_snippet, clean_snippet)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

print("✓ Fixed dangling else inside app.py!")
