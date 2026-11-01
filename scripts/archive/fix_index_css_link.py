import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace {{ url_for('static', filename='style.css') }} with direct static path /static/style.css
old_css_link = "<link rel=\"stylesheet\" href=\"{{ url_for('static', filename='style.css') }}\">"
new_css_link = "<link rel=\"stylesheet\" href=\"/static/style.css\">"

if old_css_link in html:
    html = html.replace(old_css_link, new_css_link)

# Also fix any other Jinja url_for links in index.html to direct paths
html = re.sub(r"\{\{\s*url_for\('static',\s*filename=['\"]([^'\"]+)['\"]\)\s*\}\}", r"/static/\1", html)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✓ Fixed CSS link in templates/index.html to direct /static/style.css!")
