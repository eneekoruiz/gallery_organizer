import os
import re

js_path = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\main.js"
with open(js_path, "r", encoding="utf-8") as f:
    code = f.read()

true_globals = [
    "fullGallery", "identitiesList", "currentCat", "currentIdent",
    "isMultiSelectMode", "selectedFiles", "currentFileObj", "isCurrentVideo",
    "currentFaces", "smartCleanInterval", "currentFolderItems", "currentItemIndex",
    "isSwipeModeActive", "currentPhotoFilterMode", "selectedMode", "eventsLeafletMap"
]

# We want to replace `varName` with `store.varName` EXCEPT when it is part of a declaration `var varName`, `let varName`, `const varName`
for var in true_globals:
    # First, let's just remove the top-level declarations of these variables
    code = re.sub(r'^[ \t]*(?:var|let)\s+' + var + r'\s*=[^;\n]+;\s*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^[ \t]*(?:var|let)\s+' + var + r'\s*;\s*$', '', code, flags=re.MULTILINE)

# Now, we replace `varName` with `store.varName` everywhere, unless it's preceded by `let `, `const `, `var `, or `.` (property access)
for var in true_globals:
    code = re.sub(r'(?<![\.\w])(?<!var\s)(?<!let\s)(?<!const\s)' + var + r'(?!\w)', f'store.{var}', code)

with open(js_path + ".mod", "w", encoding="utf-8") as f:
    f.write(code)
