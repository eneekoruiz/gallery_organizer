import os
import re

js_path = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\main.js"
with open(js_path, "r", encoding="utf-8") as f:
    code = f.read()

state_vars = [
    "fullGallery", "identitiesList", "currentCat", "currentIdent",
    "isMultiSelectMode", "selectedFiles", "currentFileObj", "isCurrentVideo",
    "currentFaces", "smartCleanInterval", "currentFolderItems", "currentItemIndex",
    "isSwipeModeActive", "targetName", "targetCat", "zoomLevel", "panX", "panY",
    "isPanDragging", "panStartX", "panStartY", "zoomTicking", "panTicking",
    "currentPhotoFilterMode", "selectedMode", "mapInstance", "eventsLeafletMap",
    "selectedPaths", "boxesVisible", "applyToDuplicates", "isDragging", "isResizing",
    "hasUnconfirmed", "show", "count", "groupedIds", "categories", "isDragTicking",
    "isResizeTicking", "currentHandle", "startX", "startY", "startLeft", "startTop",
    "startW", "startH", "newW", "newH", "newLeft", "newTop", "selectBox", "isDrawing"
]

# We will create store.js
store_js = "export const store = {\n"
for var in state_vars:
    # Just initialize everything to null or empty for now, or extract initial values.
    # It's easier to just do:
    store_js += f"    {var}: null,\n"
store_js += "};\n"

# But wait! selectedFiles is `new Set()`, selectedPaths is `new Set()`.
store_js = store_js.replace("selectedFiles: null,", "selectedFiles: new Set(),")
store_js = store_js.replace("selectedPaths: null,", "selectedPaths: new Set(),")
store_js = store_js.replace("currentFolderItems: null,", "currentFolderItems: [],")
store_js = store_js.replace("identitiesList: null,", "identitiesList: [],")
store_js = store_js.replace("currentFaces: null,", "currentFaces: [],")
store_js = store_js.replace("fullGallery: null,", "fullGallery: {},")
store_js = store_js.replace("isMultiSelectMode: null,", "isMultiSelectMode: false,")
store_js = store_js.replace("isSwipeModeActive: null,", "isSwipeModeActive: true,")
store_js = store_js.replace("currentItemIndex: null,", "currentItemIndex: -1,")
store_js = store_js.replace("zoomLevel: null,", "zoomLevel: 1.0,")
store_js = store_js.replace("panX: null,", "panX: 0,")
store_js = store_js.replace("panY: null,", "panY: 0,")
store_js = store_js.replace("boxesVisible: null,", "boxesVisible: true,")
store_js = store_js.replace("applyToDuplicates: null,", "applyToDuplicates: false,")

# Now, replace `var/let {var}` with nothing in the code, and rename `{var}` to `store.{var}`
# To avoid replacing inside strings or object keys, we just use regex boundary, but there might be object keys.
# Actually, since this is a complex refactor, exporting state as an object and doing string replacement is good.

# Wait, if we use window.APP_STATE, we don't have to rename anything in main.js! We can just drop `window.fullGallery` everywhere, but `store` is better.
# However, if we do `store.fullGallery`, we have to import `store` everywhere.

# Let's save store.js
os.makedirs(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\state", exist_ok=True)
with open(r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\state\store.js", "w", encoding="utf-8") as f:
    f.write(store_js)
