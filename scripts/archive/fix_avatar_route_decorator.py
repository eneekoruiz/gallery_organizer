import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_decorator_block = """@app.route('/api/person_avatar')

def find_avatar_image(target_dir):"""

new_decorator_block = """def find_avatar_image(target_dir):"""

if old_decorator_block in content:
    content = content.replace(old_decorator_block, new_decorator_block)
    content = content.replace("def api_person_avatar():", "@app.route('/api/person_avatar')\ndef api_person_avatar():")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed @app.route('/api/person_avatar') decorator position in app.py")
else:
    print("Could not match old_decorator_block in app.py")
