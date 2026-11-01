import os
import json

js_path = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\main.js.mod"
with open(js_path, "r", encoding="utf-8") as f:
    text = f.read()

with open("funcs.json", "r", encoding="utf-8") as f:
    funcs = json.load(f)

mapping = {
    'api': ['loadIdentities', 'loadGallery', 'runAnalysis', 'scanFullVideo', 'runMassCleanup', 'executeBatchMove'],
    'sidebar': ['renderTree', 'filterGallery', 'loadAlbumsHome', 'loadCategory', 'loadCategoryFilter'],
    'grid': ['filterTimeline', 'renderGrid', 'toggleMultiSelectMode', 'toggleFileSelection', 'updateBatchBar', 'clearBatchSelection', 'toggleSwipeMode', 'resetGalleryView', 'toggleSelection', 'updateFloatingBar', 'populateFabSelect', 'clearSelection'],
    'modals': ['openStatsModal', 'openIntelligentCleanup', 'checkSmartCleanStatus', 'loadSmartCleanImages', 'closeMergeModal', 'submitMergeGroup', 'openSetupModal', 'openQuickCleanMode', 'openMapModal', 'openEvolutionModal', 'openQuickCleanOverlay', 'openCompareModal', 'closeCompareModal'],
    'lightbox': ['generateReassignHTML', 'closeLightbox', 'deleteCurrentFile', 'openLightbox', 'highlightFace', 'createFaceElements', 'updateAvatarCrop', 'makeBoxInteractive', 'saveBoxDimensions', 'ignoreUnconfirmedFaces', 'quickReassignFace', 'inlineCorrect', 'swipeActionLeft', 'swipeActionRight', 'loadNextItem', 'resetZoom', 'applyZoomTransform', 'enableManualSelection', 'toggleBoxes', 'triggerDeepScanLightbox', 'toggleMetadata'],
    'helpers': ['isStableDataset', 'cleanDisplayName', 'showToast', 'forceReanalyze', 'renameCurrentGroup', 'deleteCurrentGroup', 'ignoreCurrentGroup', 'applyBulkReassign', 'applyBulkIgnore', 'performBulkAction', 'removeFromFolder', 'setPhotoFilter', 'applyPhotoFilter', 'releaseMediaElement', 'applyBulkRemoveFromFolder', 'purgeExactDuplicates', 'selectStorageMode', 'checkSetupConfig', 'saveStorageConfig', 'generateMagicShareLink', 'triggerRelearnCascade', 'autoClassifyByFilename', 'addEvolutionToHeader']
}

def get_file_for_func(name):
    for k, v in mapping.items():
        if name in v: return k
    return 'helpers'

out_code = {k: "" for k in mapping}
file_funcs = {k: [] for k in mapping}
file_funcs['app'] = []

# Sort functions by start index descending so we can replace them safely
funcs.sort(key=lambda x: x['start'], reverse=True)

for func in funcs:
    name = func['name']
    start = func['start']
    end = func['end']
    
    file_name = get_file_for_func(name)
    body = text[start:end].strip()
    
    if body.startswith('async '): exported_body = 'export ' + body
    else: exported_body = 'export ' + body
        
    out_code[file_name] = exported_body + "\n\n" + out_code[file_name]
    file_funcs[file_name].append(name)
    text = text[:start] + text[end:]

app_code = text.strip()

base_dir = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js"

def get_path(from_file, to_file):
    folder_from = "api" if from_file == "api" else "components" if from_file in ["sidebar", "grid", "modals", "lightbox"] else "utils" if from_file == "helpers" else ""
    folder_to = "api" if to_file == "api" else "components" if to_file in ["sidebar", "grid", "modals", "lightbox"] else "utils" if to_file == "helpers" else ""
    
    if from_file == "app": return f"./{folder_to}/{to_file}.js"
    if folder_from == folder_to: return f"./{to_file}.js"
    return f"../{folder_to}/{to_file}.js"

for f_name, code in out_code.items():
    if not code: continue
    folder = "api" if f_name == "api" else "components" if f_name in ["sidebar", "grid", "modals", "lightbox"] else "utils"
    
    imports = f"import {{ store }} from '../state/store.js';\n"
    for other_file, f_list in file_funcs.items():
        if other_file == f_name or not f_list or other_file == 'app': continue
        rel_path = get_path(f_name, other_file)
        imports += f"import {{ {', '.join(f_list)} }} from '{rel_path}';\n"
    
    p = os.path.join(base_dir, folder, f_name + ".js")
    with open(p, "w", encoding="utf-8") as file:
        file.write(imports + "\n" + code)

# Write app.js
app_imports = "import { store } from './state/store.js';\n"
all_funcs = []
for other_file, f_list in file_funcs.items():
    if not f_list or other_file == 'app': continue
    rel_path = get_path('app', other_file)
    app_imports += f"import {{ {', '.join(f_list)} }} from '{rel_path}';\n"
    all_funcs.extend(f_list)

window_binds = "\n".join([f"window.{f} = {f};" for f in all_funcs])
window_binds += "\nwindow.store = store;\n"

app_full = app_imports + "\n" + window_binds + "\n" + app_code
with open(os.path.join(base_dir, "app.js"), "w", encoding="utf-8") as file:
    file.write(app_full)

print("AST-based Split complete!")
