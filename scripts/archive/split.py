import os
import re

js_path = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js\main.js.mod"
with open(js_path, "r", encoding="utf-8") as f:
    text = f.read()

# Define mapping
mapping = {
    'api': ['loadIdentities', 'loadGallery', 'runAnalysis', 'scanFullVideo', 'runMassCleanup', 'executeBatchMove'],
    'sidebar': ['renderTree', 'filterGallery', 'loadAlbumsHome', 'loadCategory', 'loadCategoryFilter'],
    'grid': ['filterTimeline', 'renderGrid', 'toggleMultiSelectMode', 'toggleFileSelection', 'updateBatchBar', 'clearBatchSelection', 'toggleSwipeMode', 'resetGalleryView', 'toggleSelection', 'updateFloatingBar', 'populateFabSelect', 'clearSelection'],
    'modals': ['openStatsModal', 'openIntelligentCleanup', 'checkSmartCleanStatus', 'loadSmartCleanImages', 'closeMergeModal', 'submitMergeGroup', 'openSetupModal', 'openQuickCleanMode', 'openMapModal', 'openEvolutionModal', 'openQuickCleanOverlay', 'openCompareModal', 'closeCompareModal'],
    'lightbox': ['generateReassignHTML', 'closeLightbox', 'deleteCurrentFile', 'openLightbox', 'highlightFace', 'createFaceElements', 'updateAvatarCrop', 'makeBoxInteractive', 'saveBoxDimensions', 'ignoreUnconfirmedFaces', 'quickReassignFace', 'inlineCorrect', 'swipeActionLeft', 'swipeActionRight', 'loadNextItem', 'resetZoom', 'applyZoomTransform', 'enableManualSelection', 'toggleBoxes', 'triggerDeepScanLightbox', 'toggleMetadata'],
    'helpers': ['isStableDataset', 'cleanDisplayName', 'showToast', 'forceReanalyze', 'renameCurrentGroup', 'deleteCurrentGroup', 'ignoreCurrentGroup', 'applyBulkReassign', 'applyBulkIgnore', 'performBulkAction', 'removeFromFolder', 'setPhotoFilter', 'applyPhotoFilter', 'releaseMediaElement', 'applyBulkRemoveFromFolder', 'purgeExactDuplicates', 'selectStorageMode', 'checkSetupConfig', 'saveStorageConfig', 'generateMagicShareLink', 'triggerRelearnCascade', 'autoClassifyByFilename', 'addEvolutionToHeader']
}

out_code = {k: "" for k in mapping}
out_code['app'] = ""

def get_file_for_func(name):
    for k, v in mapping.items():
        if name in v:
            return k
    return 'app' # Default fallback

# We will regex match function declarations and replace them with nothing, moving them to the appropriate file
# A naive regex is hard, let's use a char-by-char scanner to extract them perfectly.
def extract_functions(code):
    funcs = []
    # match top level functions
    # (async )?function name(
    pattern = re.compile(r'^[ \t]*(async\s+)?function\s+([a-zA-Z0-9_]+)\s*\(', re.MULTILINE)
    
    pos = 0
    while True:
        match = pattern.search(code, pos)
        if not match:
            break
            
        start_idx = match.start()
        func_name = match.group(2)
        
        # Find the first '{'
        brace_idx = code.find('{', start_idx)
        if brace_idx == -1:
            break
            
        # Count braces
        brace_count = 1
        i = brace_idx + 1
        in_string = False
        string_char = ''
        in_comment = False
        in_multiline = False
        
        while i < len(code) and brace_count > 0:
            c = code[i]
            
            if in_string:
                if c == '\\':
                    i += 2
                    continue
                if c == string_char:
                    in_string = False
            elif in_comment:
                if c == '\n':
                    in_comment = False
            elif in_multiline:
                if c == '*' and i+1 < len(code) and code[i+1] == '/':
                    in_multiline = True
                    i += 1
            else:
                if c in ('"', "'", '`'):
                    in_string = True
                    string_char = c
                elif c == '/' and i+1 < len(code) and code[i+1] == '/':
                    in_comment = True
                    i += 1
                elif c == '/' and i+1 < len(code) and code[i+1] == '*':
                    in_multiline = True
                    i += 1
                elif c == '{':
                    brace_count += 1
                elif c == '}':
                    brace_count -= 1
                    
            i += 1
            
        end_idx = i
        func_body = code[start_idx:end_idx]
        funcs.append((func_name, func_body, start_idx, end_idx))
        pos = end_idx
        
    return funcs

funcs = extract_functions(text)

# We must remove them from back to front to not mess up indices
for name, body, start, end in reversed(funcs):
    file_name = get_file_for_func(name)
    # Add export
    exported_body = body.strip()
    if exported_body.startswith('async '):
        exported_body = 'export ' + exported_body
    else:
        exported_body = 'export ' + exported_body
        
    out_code[file_name] = exported_body + "\n\n" + out_code[file_name]
    
    # Remove from text
    text = text[:start] + text[end:]

out_code['app'] = text.strip()

base_dir = r"C:\Users\User\Desktop\ENEKO\smart_gallery_app\static\js"
for f_name, code in out_code.items():
    if not code: continue
    folder = "api" if f_name == "api" else "components" if f_name in ["sidebar", "grid", "modals", "lightbox"] else "utils" if f_name == "helpers" else ""
    # if app, it's just in js/
    p = os.path.join(base_dir, folder, f_name + ".js") if folder else os.path.join(base_dir, f_name + ".js")
    
    with open(p, "w", encoding="utf-8") as file:
        # We need to import store everywhere except in state
        header = "import { store } from '../state/store.js';\n\n" if folder else "import { store } from './state/store.js';\n\n"
        if folder:
            file.write(header + code)
        else:
            # For app.js, we need to import all exported functions and assign to window
            # We will generate this next
            file.write(code)

print("Split complete!")
