import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_detect_call = """            detector.setInputSize((w, h))
            _, faces = detector.detect(img)"""

new_detect_call = """            h, w = img.shape[:2]
            detector.setInputSize((w, h))
            _, faces = detector.detect(img)"""

# Make sure setInputSize is called inside try block in api_analyze
if "detector.detect(img)" in content:
    content = content.replace("_, faces = detector.detect(img)", "h_f, w_f = img.shape[:2]\n            detector.setInputSize((w_f, h_f))\n            _, faces = detector.detect(img)")
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched setInputSize before detect in api_analyze")
