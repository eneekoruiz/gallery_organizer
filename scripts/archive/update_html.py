import os
path = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\templates\index.html"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('<script src="/static/js/main.js"></script>', '<script type="module" src="/static/js/app.js"></script>')

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
