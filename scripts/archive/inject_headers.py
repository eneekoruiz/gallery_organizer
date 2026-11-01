import sys

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

injection = """
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.after_request
def add_header(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response
"""

if '@app.after_request' not in content:
    content = content.replace("def index():\n    return render_template('index.html')", "def index():\n    return render_template('index.html')\n" + injection)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Injected cache-control and favicon routes')
else:
    print('Already injected')
