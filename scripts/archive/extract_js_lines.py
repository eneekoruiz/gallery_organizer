import os

html_path = "templates/index.html"
js_path = "static/js/main.js"

with open(html_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_html_lines = []
js_lines = []

in_script = False
is_external = False

for line in lines:
    if "<script" in line and "</script>" in line:
        if "src=" in line:
            new_html_lines.append(line)
        else:
            # Inline one-liner script
            start = line.find(">") + 1
            end = line.find("</script>")
            js_lines.append(line[start:end])
    elif "<script" in line:
        if "src=" in line:
            new_html_lines.append(line)
            is_external = True
        else:
            in_script = True
    elif "</script>" in line:
        if in_script:
            in_script = False
            js_lines.append("\n\n")
        elif is_external:
            new_html_lines.append(line)
            is_external = False
    else:
        if in_script:
            js_lines.append(line)
        else:
            new_html_lines.append(line)

# Add script src just before </body>
for i, line in enumerate(new_html_lines):
    if "</body>" in line:
        new_html_lines.insert(i, '    <script src="/static/js/main.js"></script>\n')
        break

with open(html_path, "w", encoding="utf-8") as f:
    f.writelines(new_html_lines)

with open(js_path, "w", encoding="utf-8") as f:
    f.writelines(js_lines)

print("Extraction complete.")
print(f"JS lines: {len(js_lines)}")
print(f"HTML lines: {len(new_html_lines)}")
