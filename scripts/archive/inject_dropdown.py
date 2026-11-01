import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

func = """        function generateReassignHTML(face, faceNum, onchangeFuncName) {
            let pathParts = currentFileObj.path.split(/[\\\\/]/);
            let folderName = pathParts.slice(-2, -1)[0];
            let categoryName = pathParts.slice(-3, -2)[0];
            if (folderName === '_Dudosos') {
                folderName = pathParts.slice(-3, -2)[0];
                categoryName = pathParts.slice(-4, -3)[0];
            }
            
            let aiPredictedIdObj = null;
            if (face.identity && face.identity !== 'Desconocido' && face.identity !== folderName) {
                aiPredictedIdObj = identitiesList.find(id => id.identidad === face.identity);
            }
            
            let html = `<div class="custom-dropdown" style="position:relative; width:100%; text-align:left;">`;
            html += `<button class="custom-dropdown-btn" onclick="let menu = document.getElementById('menu-${faceNum}-${onchangeFuncName}'); menu.style.display = menu.style.display==='block'?'none':'block'; event.stopPropagation();" style="width:100%; padding:8px; border-radius:6px; background:#333; color:white; border:1px solid #555; cursor:pointer; text-align:left; font-size:14px; display:flex; justify-content:space-between;"><span>Reasignar persona...</span><span>▾</span></button>`;
            html += `<div class="custom-dropdown-menu" id="menu-${faceNum}-${onchangeFuncName}" style="display:none; position:absolute; top:100%; left:0; width:220px; max-height:280px; overflow-y:auto; background:#1c1c1e; border:1px solid #444; z-index:99999; border-radius:8px; padding:4px; margin-top:4px; box-shadow:0 10px 30px rgba(0,0,0,0.8);">`;
            
            const btnStyle = "display:block; width:100%; text-align:left; padding:8px 10px; background:transparent; border:none; color:white; cursor:pointer; border-radius:4px; font-size:13px; margin-bottom:2px; transition:background 0.2s;";
            const hoverScript = "onmouseover=\\"this.style.background='#3a3a3c'\\" onmouseout=\\"this.style.background='transparent'\\"";
            
            const makeBtn = (valObj, text, color="white", fontWeight="normal") => {
                let valStr = valObj === 'NEW' ? 'NEW' : JSON.stringify(valObj).replace(/"/g, '&quot;');
                let call = `${onchangeFuncName}('${valStr}', ${faceNum})`;
                return `<button style="${btnStyle} color:${color}; font-weight:${fontWeight};" ${hoverScript} onclick="document.getElementById('menu-${faceNum}-${onchangeFuncName}').style.display='none'; ${call}">${text}</button>`;
            };
            
            if (aiPredictedIdObj) {
                html += makeBtn(aiPredictedIdObj, `🤖 Confirmar IA: ${face.identity}`, '#0a84ff', 'bold');
            }
            
            if (folderName && categoryName && folderName !== 'Resultados' && categoryName !== 'Galeria Eneko NO ABRIR') {
                if (!aiPredictedIdObj) {
                    html += makeBtn({categoria: categoryName, identidad: folderName}, `✨ Sí, es (Dueño): ${folderName}`, '#30d158', 'bold');
                }
                html += makeBtn({categoria: '_Dudosos', identidad: 'Desconocido'}, `🤔 Esto NO es ${folderName} (Dudoso)`, '#ff9f0a', 'bold');
            }
            
            html += makeBtn({categoria: 'Ignorar', identidad: 'Ignorar_Irrelevante'}, `👤 Ignorar cara (Irrelevante)`, '#ccc');
            html += makeBtn({categoria: 'Ignorar', identidad: 'Falso_Positivo'}, `🚫 Esto NO es una cara`, '#ff453a');
            html += makeBtn('NEW', `➕ Crear nueva persona...`, 'white', 'bold');
            
            html += `<hr style="border:0; border-top:1px solid #333; margin:6px 0;">`;
            
            let categories = {};
            identitiesList.forEach(id => {
                if(!categories[id.categoria]) categories[id.categoria] = [];
                categories[id.categoria].push(id);
            });
            
            Object.keys(categories).sort().forEach(cat => {
                html += `<details style="margin-bottom:4px;">`;
                html += `<summary style="cursor:pointer; padding:6px 10px; font-weight:bold; color:#aaa; font-size:12px; background:#2c2c2e; border-radius:4px; margin-bottom:2px;">${cat}</summary>`;
                html += `<div style="padding-left:8px; border-left:2px solid #333; margin-left:10px;">`;
                categories[cat].sort((a,b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    html += makeBtn(id, id.identidad);
                });
                html += `</div></details>`;
            });
            
            html += `</div></div>`;
            return html;
        }
"""

if 'function generateReassignHTML' not in content:
    content = content.replace('function showToast(', func + '\n        function showToast(')
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Injected generateReassignHTML')
else:
    print('Already injected')
