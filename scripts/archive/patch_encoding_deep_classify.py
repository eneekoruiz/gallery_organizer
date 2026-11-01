import sys

with open('deep_auto_classify_all.py', 'r', encoding='utf-8') as f:
    content = f.read()

if "sys.stdout.reconfigure(encoding='utf-8')" not in content:
    content = "import sys\ntry:\n    sys.stdout.reconfigure(encoding='utf-8')\nexcept:\n    pass\n\n" + content
    with open('deep_auto_classify_all.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched sys.stdout encoding in deep_auto_classify_all.py")
