import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace currentAnalysisPath with currentFileObj.path
old_remove = """async function removeFromFolder() {
    if (!currentAnalysisPath || !currentCat || !currentIdent) return;"""

new_remove = """async function removeFromFolder() {
    if (!currentFileObj || !currentFileObj.path || !currentCat || !currentIdent) return;
    const currentAnalysisPath = currentFileObj.path;"""

if old_remove in content:
    content = content.replace(old_remove, new_remove)

old_deep = """function triggerDeepScanLightbox() {
    if (!currentAnalysisPath) return;"""

new_deep = """function triggerDeepScanLightbox() {
    if (!currentFileObj || !currentFileObj.path) return;
    const currentAnalysisPath = currentFileObj.path;"""

if old_deep in content:
    content = content.replace(old_deep, new_deep)

old_run_analysis = "runAnalysis(currentAnalysisPath);"
new_run_analysis = "openLightbox(currentFileObj);"

if old_run_analysis in content:
    content = content.replace(old_run_analysis, new_run_analysis)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed currentAnalysisPath in index.html")
