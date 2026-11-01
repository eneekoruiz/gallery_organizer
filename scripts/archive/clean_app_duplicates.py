import sys

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_mode = False

for i, line in enumerate(lines):
    # If line 1305 has pass(src, dst):
    if 'pass(src, dst):' in line:
        new_lines.append('        pass\n')
        skip_mode = True
        continue
        
    if skip_mode:
        if line.startswith('def ') or line.startswith('@app.route') or line.startswith('if __name__'):
            skip_mode = False
            new_lines.append(line)
        continue
        
    if line.strip() == 'def safe_move_file(src, dst):' and i > 200:
        skip_mode = True
        continue
        
    new_lines.append(line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Cleaned up duplicated helper functions in app.py")
