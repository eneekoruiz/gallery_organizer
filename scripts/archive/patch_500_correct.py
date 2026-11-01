import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix final_target_path returning Path object instead of string
old_return = 'return jsonify({"success": True, "new_path": final_target_path})'
new_return = 'return jsonify({"success": True, "new_path": str(final_target_path)})'

if old_return in content:
    content = content.replace(old_return, new_return)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched app.py (api_correct 500 fix)")
else:
    print("Could not find old_return in app.py")
