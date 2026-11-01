import os
import re

js_path = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\main.js.mod"
with open(js_path, "r", encoding="utf-8") as f:
    text = f.read()

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

def extract_functions(code):
    funcs = []
    pattern = re.compile(r'^[ \t]*(async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
    pos = 0
    while True:
        match = pattern.search(code, pos)
        if not match: break
        start_idx = match.start()
        func_name = match.group(2)
        brace_idx = code.find('{', start_idx)
        if brace_idx == -1: break
        
        brace_count = 1
        i = brace_idx + 1
        in_string, string_char, in_comment, in_multiline = False, '', False, False
        
        while i < len(code) and brace_count > 0:
            c = code[i]
            if in_string:
                if c == '\\': i += 2; continue
                if c == string_char: in_string = False
            elif in_comment:
                if c == '\n': in_comment = False
            elif in_multiline:
                if c == '*' and i+1 < len(code) and code[i+1] == '/': in_multiline = True; i += 1
            else:
                if c in ('"', "'", '`'): in_string = True; string_char = c
                elif c == '/' and i+1 < len(code) and code[i+1] == '/': in_comment = True; i += 1
                elif c == '/' and i+1 < len(code) and code[i+1] == '*': in_multiline = True; i += 1
                elif c == '{': brace_count += 1
                elif c == '}': brace_count -= 1
            i += 1
            
        end_idx = i
        func_body = code[start_idx:end_idx]
        funcs.append((func_name, func_body, start_idx, end_idx))
        pos = end_idx
    return funcs

funcs = extract_functions(text)

file_funcs = {k: [] for k in mapping}
file_funcs['app'] = []

out_code = {k: "" for k in mapping}

for name, body, start, end in reversed(funcs):
    file_name = get_file_for_func(name)
    exported_body = body.strip()
    if exported_body.startswith('async '): exported_body = 'export ' + exported_body
    else: exported_body = 'export ' + exported_body
        
    out_code[file_name] = exported_body + "\n\n" + out_code[file_name]
    file_funcs[file_name].append(name)
    text = text[:start] + text[end:]

app_code = text.strip()

base_dir = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js"

# Generate import block for each file
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

print("Split and imports complete!")
