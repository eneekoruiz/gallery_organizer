import sys

with open('static/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

old_css = """
.lb-bb-badge {
    position: absolute;
    top: -6px;
    left: -6px;
"""
new_css = """
.lb-bb-badge {
    position: absolute;
    top: -14px;
    left: 50%;
    transform: translateX(-50%);
"""

if old_css in css:
    css = css.replace(old_css, new_css)
    with open('static/style.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("Patched badge position in CSS")
else:
    print("Could not find badge css")
