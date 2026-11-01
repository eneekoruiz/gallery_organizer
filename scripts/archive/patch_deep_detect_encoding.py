import sys

with open('deep_detect_familia_folders.py', 'r', encoding='utf-8') as f:
    content = f.read()

if "sys.stdout.reconfigure" not in content:
    content = "import sys\ntry:\n    sys.stdout.reconfigure(encoding='utf-8')\nexcept:\n    pass\n\n" + content
    with open('deep_detect_familia_folders.py', 'w', encoding='utf-8') as f:
        f.write(content)
