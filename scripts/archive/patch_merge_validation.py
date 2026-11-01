import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix submitMergeGroup validation
old_submit_start = """        async function submitMergeGroup() {
            const existingNameJSON = document.getElementById('merge-selected-value').value;"""

new_submit_start = """        async function submitMergeGroup() {
            if (!currentCat || !currentIdent) {
                alert("Por favor, selecciona una carpeta o persona antes de intentar fusionar.");
                closeMergeModal();
                return;
            }
            const existingNameJSON = document.getElementById('merge-selected-value').value;"""

if old_submit_start in content:
    content = content.replace(old_submit_start, new_submit_start)

# Fix renameCurrentGroup validation
old_rename_start = """        function renameCurrentGroup() {
            if (!currentCat || !currentIdent || currentCat !== 'Personas Sin Nombre') return;"""

new_rename_start = """        function renameCurrentGroup() {
            if (!currentCat || !currentIdent) {
                alert("Selecciona primero una persona en la barra lateral para poder fusionarla.");
                return;
            }"""

if old_rename_start in content:
    content = content.replace(old_rename_start, new_rename_start)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched merge validations in index.html")
