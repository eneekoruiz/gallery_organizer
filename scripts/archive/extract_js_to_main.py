import os
import re

html_path = "templates/index.html"
js_path = "static/js/main.js"

with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

script_pattern = re.compile(r'<script\b[^>]*>(.*?)</script>', re.DOTALL)

def script_replacer(match):
    tag = match.group(0)
    if 'src=' in tag:
        return tag # Keep external scripts
    return ""

new_html = re.sub(r'<script\b[^>]*>(.*?)</script>', script_replacer, html_content, flags=re.DOTALL)

if '</body>' in new_html:
    new_html = new_html.replace('</body>', '    <script src="/static/js/main.js"></script>\n</body>')
else:
    new_html += '\n<script src="/static/js/main.js"></script>'

combined_js = ""
for script in script_pattern.finditer(html_content):
    if 'src=' not in script.group(0):
        combined_js += script.group(1) + "\n\n"

with open(js_path, "w", encoding="utf-8") as f:
    f.write(combined_js)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_html)

print(f"Extracted JS to {js_path}. Kept HTML size: {len(new_html)}")
