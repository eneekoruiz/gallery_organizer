import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    app_content = f.read()

if "document.getElementById('merge-existing-select').value" in app_content:
    app_content = app_content.replace("document.getElementById('merge-existing-select').value", "document.getElementById('merge-selected-value').value")
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(app_content)
    print("Patched submitMergeGroup to use correct hidden input")
else:
    print("Could not find the string to replace")
