import sys

# 1. Patch app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

if 'import sys' not in app_content:
    app_content = app_content.replace('import subprocess', 'import subprocess\nimport sys')

if 'return "Bad image", 500' in app_content:
    app_content = app_content.replace('return "Bad image", 500', 'return "Bad image", 404')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

# 2. Patch index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Remove the block that causes ReferenceError for aiPredictedIdObj
block_to_remove = """
            if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                if (!aiPredictedIdObj) {
                    let suggestedId = {categoria: categoryName, identidad: folderName};
                    selectOptionsHtml += `<option value='${JSON.stringify(suggestedId)}' style="font-weight:bold; color:#30d158;">✨ Sí, es (Dueño): ${folderName}</option>`;
                }
            }
"""
if block_to_remove in html_content:
    html_content = html_content.replace(block_to_remove, "")

# Fix the currentFileObj.path error
error_line = "currentFileObj.path = data.new_path.replace(/\\\\\\\\/g, '/');"
fixed_line = "if (currentFileObj) currentFileObj.path = data.new_path.replace(/\\\\\\\\/g, '/');"
if error_line in html_content:
    html_content = html_content.replace(error_line, fixed_line)
else:
    # Also try with single slashes in the python string literal
    error_line_2 = "currentFileObj.path = data.new_path.replace(/\\\\/g, '/');"
    fixed_line_2 = "if (currentFileObj) currentFileObj.path = data.new_path.replace(/\\\\/g, '/');"
    if error_line_2 in html_content:
        html_content = html_content.replace(error_line_2, fixed_line_2)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("All patches applied successfully")
