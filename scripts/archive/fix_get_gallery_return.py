import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Define helper block to place right after imports
helpers_code = """
import gc, time, shutil, os

def safe_move_file(src, dst):
    src_str, dst_str = str(src), str(dst)
    gc.collect()
    for attempt in range(5):
        try:
            shutil.move(src_str, dst_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    try:
        shutil.copy2(src_str, dst_str)
        try:
            os.remove(src_str)
        except:
            pass
        return True
    except Exception as e:
        raise e

def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False
"""

# Extract get_gallery block to remove misplaced functions inside it
bad_inner_block = """    dup_data = {}
    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass

def safe_move_file(src, dst):
    src_str, dst_str = str(src), str(dst)
    gc.collect()
    for attempt in range(5):
        try:
            shutil.move(src_str, dst_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    try:
        shutil.copy2(src_str, dst_str)
        try:
            os.remove(src_str)
        except:
            pass
        return True
    except Exception as e:
        raise e

def safe_remove_file(filepath):
    f_str = str(filepath)
    gc.collect()
    for attempt in range(5):
        try:
            os.remove(f_str)
            return True
        except PermissionError:
            time.sleep(0.2)
            gc.collect()
    return False

    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass"""

clean_inner_block = """    dup_data = {}
    try:
        with open('duplicate_groups.json', 'r') as df:
            dup_data = json.load(df)
    except:
        pass"""

if bad_inner_block in content:
    content = content.replace(bad_inner_block, clean_inner_block)

# Put helpers_code after app = Flask(...)
if 'def safe_move_file' in content:
    # Remove any existing safe_move_file definitions
    lines = content.split('\n')
    new_lines = []
    skip = False
    for line in lines:
        if line.startswith('def safe_move_file(') or line.startswith('def safe_remove_file('):
            skip = True
            continue
        if skip:
            if line.startswith('def ') or line.startswith('@app.route') or line.startswith('if ') or line.startswith('class '):
                skip = False
                new_lines.append(line)
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

# Now insert helpers_code right before @app.route('/api/gallery')
if "@app.route('/api/gallery')" in content:
    content = content.replace("@app.route('/api/gallery')", helpers_code + "\n\n@app.route('/api/gallery')")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Re-structured app.py and fixed get_gallery return statement")
