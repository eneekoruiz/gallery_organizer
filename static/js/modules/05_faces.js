/**
 * SmartGallery AI - FACE DETECTION, CROP & INLINE CORRECTIONS
 * Module: static/js/modules/05_faces.js
 */

        function generateReassignHTML(face, faceNum, onchangeFuncName, sourceContext='default') {
            let pathParts = (currentFileObj && currentFileObj.path) ? currentFileObj.path.split(/[\\\/]/) : [];
            let folderName = pathParts.length >= 2 ? pathParts.slice(-2, -1)[0] : '';
            let categoryName = pathParts.length >= 3 ? pathParts.slice(-3, -2)[0] : '';

            if (folderName === '_Dudosos') {
                folderName = pathParts.length >= 3 ? pathParts.slice(-3, -2)[0] : '';

                categoryName = pathParts.length >= 4 ? pathParts.slice(-4, -3)[0] : '';
            }

            const isInvalidFolderName = (name) => {
                if (!name) return true;

                const lower = name.toLowerCase().trim();
                const invalidExact = [
                    'fotos', 'resultados', 'galeria eneko no abrir',

                    'familia', 'conocidos', 'profesores', 'mascotas',

                    'yo', 'amigos', 'otros', 'desconocidos', 'desconocido',

                    'photos', 'icloud', 'icloud photos', 'pictures', 'imagenes', 'imágenes'
                ];

                if (invalidExact.includes(lower)) return true;

                const invalidSubstrings = [
                    'conmigo', 'sin mi', 'sin mí', 'grupales', 'con amigos', 'familiares',

                    'para revisar', 'revisar', 'dudosos', '_dudosos',

                    'personas sin nombre', 'limpieza inteligente',

                    'recuerdos', 'lugares', 'eventos', 'frases',

                    'por organizar', 'pendientes', 'masivos'
                ];

                if (invalidSubstrings.some(inv => lower.includes(inv))) return true;

                if (name.startsWith('_') || name.startsWith('📋') || name.startsWith('⏳') || name.startsWith('!') || name.startsWith('⚠️') || name.startsWith('❓') || name.startsWith('🎬') || name.startsWith('📷') || name.startsWith('👤')) return true;

                return false;
            };

            const isRealPersonFolder = !isInvalidFolderName(folderName) && Boolean(folderName.match(/^[CFPM]\.?\s+/i) || folderName === 'YO' || (typeof identitiesList !== 'undefined' && identitiesList.some(id => id.identidad === folderName)));

            // Determinar si la cara ya tiene una identidad humana asignada/confirmada

            const isAssignedToPerson = face.identity &&

                face.identity !== 'Desconocido' &&

                !face.identity.startsWith('IA (Pendiente)');

            // ── Determine AI suggestion & claimed people in photo (Strict Mutual Exclusion) ──

            const otherAssignedInPhoto = new Set();
            let ownerAlreadyIdentified = false;

            if (typeof currentFaces !== 'undefined' && Array.isArray(currentFaces)) {
                currentFaces.forEach((f, idx) => {
                    if (idx !== faceNum - 1) {
                        const rawId = f.identity || '';
                        const cleanId = rawId.replace(/^\?\s*/, '').trim();
                        const isNonPerson = !cleanId || cleanId === 'Desconocido' || cleanId.startsWith('IA ') || cleanId.startsWith('Falso_') || cleanId.startsWith('Ignorar_') || cleanId.includes('(Sin rostro') || cleanId.toLowerCase().includes('desconocid');

                        if (!isNonPerson) {
                            otherAssignedInPhoto.add(cleanId);

                            otherAssignedInPhoto.add(rawId);

                            if (cleanId === folderName || rawId === folderName || f.tag_type === 'dataset' || f.is_owner || f.is_centroid) {
                                ownerAlreadyIdentified = true;

                                if (folderName) otherAssignedInPhoto.add(folderName);
                            }
                        }

                        if (f.is_manual && cleanId) {
                            otherAssignedInPhoto.add(cleanId);

                            if (cleanId === folderName) {
                                ownerAlreadyIdentified = true;

                                if (folderName) otherAssignedInPhoto.add(folderName);
                            }
                        }
                    }
                });
            }

            let aiPredictedIdObj = null;
            let hasAiSuggestion = false;
            let suggestedName = face.suggested_identity;

            if (!suggestedName && face.identity) {
                if (face.identity.startsWith('? ')) {
                    const candidate = face.identity.replace(/^\?\s*/, '').trim();

                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                } else if (face.identity.startsWith('IA (Pendiente): ')) {
                    const candidate = face.identity.replace('IA (Pendiente): ', '').trim();

                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                } else if (face.identity.startsWith('IA: ')) {
                    const candidate = face.identity.replace('IA: ', '').trim();

                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                } else if (!face.is_manual && face.identity !== 'Desconocido' && !face.identity.startsWith('Falso_') && !face.identity.startsWith('Ignorar_')) {
                    const candidate = face.identity.replace(/^\?\s*/, '').trim();

                    if (!(candidate === folderName && ownerAlreadyIdentified)) {
                        suggestedName = candidate;
                    }
                }
            }

            // Exclusión mutua: una persona NO puede repetirse en varias caras de la misma foto

            if (suggestedName && otherAssignedInPhoto.has(suggestedName)) {
                suggestedName = null;
            }

            // Si la sugerencia es el dueño del álbum y el dueño ya ha sido identificado en otra cara, anular

            if (suggestedName && suggestedName === folderName && ownerAlreadyIdentified) {
                suggestedName = null;
            }

            // Si esta cara YA es el dueño confirmado (sin duda), no mostrar sugerencia de sí mismo

            if (suggestedName && face.identity === folderName && !face.identity.startsWith('? ')) {
                suggestedName = null;
            }

            if (suggestedName && !isInvalidFolderName(suggestedName)) {
                const cleanSugg = suggestedName.replace(/^\?\s*/, '').trim();
                const matchedObj = identitiesList.find(id => id.identidad === cleanSugg || id.identidad === suggestedName);

                aiPredictedIdObj = matchedObj ? {categoria: matchedObj.categoria, identidad: cleanSugg} : {categoria: categoryName || 'Familia', identidad: cleanSugg};

                if (aiPredictedIdObj) hasAiSuggestion = true;
            }

            const menuId = `menu-${faceNum}-${sourceContext}-${onchangeFuncName}`;
            const makeAction = (valObj, label, bg, color, fw='600') => {
                let valStr = valObj === 'NEW' ? 'NEW' : JSON.stringify(valObj).replace(/"/g, '&quot;');
                let call = `${onchangeFuncName}('${valStr}', ${faceNum})`;

                return `<button onclick="let m=document.getElementById('${menuId}'); if(m) m.style.display='none'; ${call}" style="

                    display:flex; align-items:center; gap:5px; width:100%;

                    padding:7px 10px; border-radius:8px; border:1px solid ${bg}33;

                    background:${bg}18; color:${color}; cursor:pointer;

                    font-size:11px; font-weight:${fw}; transition:all 0.15s; text-align:left;

                " onmouseover="this.style.background='${bg}35'" onmouseout="this.style.background='${bg}18'">${label}</button>`;
            };

            let html = `<div style="display:flex; flex-direction:column; gap:5px; margin-top:6px;">`;

            // ── 1. AI SUGGESTION CHIP (most prominent) ──────────

            if (hasAiSuggestion) {
                const confirmVal = JSON.stringify(aiPredictedIdObj).replace(/"/g, '&quot;');
                const rejectVal  = JSON.stringify({categoria: '_Dudosos', identidad: 'Desconocido'}).replace(/"/g, '&quot;');

                html += `

                <div style="background:rgba(10,132,255,0.1); border:1px solid rgba(10,132,255,0.3); border-radius:10px; padding:8px 10px;">

                    <div style="font-size:10px; color:#64d2ff; font-weight:700; letter-spacing:0.5px; margin-bottom:6px; display:flex; align-items:center; gap:4px;">

                        <span>🤖</span> SUGERENCIA IA

                    </div>

                    <div style="font-size:12px; color:#fff; font-weight:600; margin-bottom:7px; padding:0 2px;">${(suggestedName||'').replace(/^\?\s*/, '')}${face.suggested_score ? ` (${Math.round(face.suggested_score * 100)}% certeza)` : ''}</div>

                    <div style="display:flex; gap:5px;">

                        <button onclick="${onchangeFuncName}('${confirmVal}', ${faceNum})" style="

                            flex:1; padding:6px 4px; border-radius:7px; border:1px solid #30d15855;

                            background:rgba(48,209,88,0.15); color:#30d158; cursor:pointer;

                            font-size:11px; font-weight:700; transition:all 0.15s;

                        " onmouseover="this.style.background='rgba(48,209,88,0.3)'" onmouseout="this.style.background='rgba(48,209,88,0.15)'">

                            ✓ Sí, es ${(suggestedName||'').replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '')}

                        </button>

                        <button onclick="${onchangeFuncName}('${rejectVal}', ${faceNum})" style="

                            flex:1; padding:6px 4px; border-radius:7px; border:1px solid #ff453a55;

                            background:rgba(255,69,58,0.12); color:#ff6961; cursor:pointer;

                            font-size:11px; font-weight:700; transition:all 0.15s;

                        " onmouseover="this.style.background='rgba(255,69,58,0.28)'" onmouseout="this.style.background='rgba(255,69,58,0.12)'">

                            ✗ No es ${(suggestedName||'').replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '')}

                        </button>

                    </div>

                </div>`;
            }

            // ── 2. Album owner confirm ONLY IF face is unassigned/unknown AND it's a real person album AND owner is NOT already identified in this photo ──

            if (isRealPersonFolder && !isAssignedToPerson && !hasAiSuggestion && !ownerAlreadyIdentified && !otherAssignedInPhoto.has(folderName)) {
                html += makeAction(
                    {categoria: categoryName, identidad: folderName},

                    `✨ Sí, es ${folderName} (dueño del álbum)`,

                    '#30d158', '#30d158'
                );

                html += makeAction(
                    {categoria: '_Dudosos', identidad: 'Desconocido'},

                    `❌ Esta cara NO es ${folderName}`,

                    '#ff9f0a', '#ff9f0a'
                );
            }

            // ── 2b. Explicit rejection if face has non-manual identity and not already suggested

            if (!hasAiSuggestion && face.identity && face.identity !== 'Desconocido' && !face.is_manual) {
                const cleanIdentName = face.identity.replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '').replace(/^IA:\s*/i, '').trim();

                html += makeAction({categoria: '_Dudosos', identidad: 'Desconocido'}, `❌ Esta persona NO es ${cleanIdentName}`, '#ff453a', '#ff6961', '700');
            }

            // ── 3. Quick Discard actions ───────────────────────────

            html += makeAction({categoria: 'Ignorar', identidad: 'Falso_Positivo'}, '🚫 Esto NO es una cara', '#ff453a', '#ff453a', '500');

            html += makeAction({categoria: 'Ignorar', identidad: 'Ignorar_Irrelevante'}, '👤 Ignorar (irrelevante)', '#8e8e93', '#8e8e93', '500');

            // ── 4. Full reassign dropdown ────────────────────────

            let categories = {};

            identitiesList.forEach(id => {
                if (!categories[id.categoria]) categories[id.categoria] = [];

                categories[id.categoria].push(id);
            });

            const dropBtnStyle = `display:flex; justify-content:space-between; align-items:center; width:100%; padding:7px 10px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); cursor:pointer; font-size:11px; font-weight:600; transition:all 0.15s;`;

            html += `<div style="position:relative; width:100%;">`;

            html += `<button onclick="openReassignFaceModal(${faceNum}, '${onchangeFuncName}'); event.stopPropagation();" style="${dropBtnStyle}" title="Abrir selector con búsqueda"><span>↔ Reasignar a otra persona...</span><span style="opacity:0.7; font-size:12px;">🔍 ▾</span></button>`;

            html += `<div id="${menuId}" style="display:none; position:relative; width:100%; margin-top:6px; max-height:260px; overflow-y:auto; background:#141416; border:1px solid rgba(255,255,255,0.15); z-index:99999; border-radius:10px; padding:6px; box-shadow:0 8px 24px rgba(0,0,0,0.85);" class="custom-scrollbar">`;

            const innerBtnStyle = `display:block; width:100%; text-align:left; padding:7px 10px; background:transparent; border:none; color:rgba(255,255,255,0.8); cursor:pointer; border-radius:6px; font-size:12px; transition:background 0.15s;`;
            const hoverScript = `onmouseover="this.style.background='rgba(255,255,255,0.08)'" onmouseout="this.style.background='transparent'"`;

            // "Nueva persona" option

            html += `<button style="${innerBtnStyle} color:#0a84ff; font-weight:600;" ${hoverScript} onclick="let m=document.getElementById('${menuId}'); if(m) m.style.display='none'; ${onchangeFuncName}('NEW', ${faceNum})">➕ Nueva persona...</button>`;

            html += `<hr style="border:0; border-top:1px solid rgba(255,255,255,0.08); margin:4px 0;">`;

            Object.keys(categories).sort().forEach(cat => {
                html += `<details style="margin-bottom:2px;">`;

                html += `<summary style="cursor:pointer; padding:5px 8px; font-weight:700; color:rgba(255,255,255,0.4); font-size:10px; text-transform:uppercase; letter-spacing:0.6px; background:rgba(255,255,255,0.04); border-radius:5px; margin-bottom:2px; list-style:none; display:flex; align-items:center; gap:4px;">▸ ${cat}</summary>`;

                categories[cat].sort((a, b) => a.identidad.localeCompare(b.identidad)).forEach(id => {
                    const isAlreadyInPhoto = otherAssignedInPhoto.has(id.identidad);

                    if (isAlreadyInPhoto) {
                        html += `<button disabled style="${innerBtnStyle} opacity:0.35; cursor:not-allowed;" title="Esta persona ya ha sido identificada en otra cara de esta misma foto">🚫 ${typeof cleanDisplayName === 'function' ? cleanDisplayName(id.identidad) : id.identidad} <span style="font-size:9px; color:#ff9f0a; font-weight:700;">(Ya en foto)</span></button>`;
                    } else {
                        const vs = JSON.stringify(id).replace(/"/g, '&quot;');

                        html += `<button style="${innerBtnStyle}" ${hoverScript} onclick="let m=document.getElementById('${menuId}'); if(m) m.style.display='none'; ${onchangeFuncName}('${vs}', ${faceNum})">${typeof cleanDisplayName === 'function' ? cleanDisplayName(id.identidad) : id.identidad}</button>`;
                    }
                });

                html += `</details>`;
            });

            html += `</div></div>`;

            html += `</div>`;

            return html;
        }

        function showToast(message, isError=false) {
            let container = document.getElementById('toast-container');

            if (!container) {
                container = document.createElement('div');

                container.id = 'toast-container';

                container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;';

                document.body.appendChild(container);
            }

            const toast = document.createElement('div');

            toast.style.cssText = `background: ${isError ? 'rgba(255, 59, 48, 0.9)' : 'rgba(10, 132, 255, 0.9)'}; color: white; padding: 12px 20px; border-radius: 8px; backdrop-filter: blur(10px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); font-family: -apple-system, sans-serif; font-size: 13px; transform: translateX(120%); transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);`;

            toast.innerHTML = `<strong>${isError ? 'Aviso' : 'Información'}</strong><br>${message}`;

            container.appendChild(toast);

            requestAnimationFrame(() => toast.style.transform = 'translateX(0)');

            setTimeout(() => {
                toast.style.transform = 'translateX(120%)';

                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        async function loadIdentities() {
            try {
                const res = await fetch('/api/identities');

                if (res.ok) {
                    identitiesList = await res.json();
                }
            } catch (e) {
                console.warn('loadIdentities non-blocking notice:', e);
            }
        }

                let statsPollInterval = null;
        let lastStatsData = null;

        window.closeStatsModal = function() {
            const modal = document.getElementById('stats-modal');

            if (modal) modal.style.display = 'none';

            if (statsPollInterval) {
                clearInterval(statsPollInterval);

                statsPollInterval = null;
            }
        };

        window.openStatsModal = async function(isManualRefresh = false) {
            const modal = document.getElementById('stats-modal');

            if (!modal) return;

            modal.style.display = 'flex';

            const refreshIcon = document.getElementById('stats-refresh-icon');

            if (refreshIcon) refreshIcon.style.animation = 'spin 0.8s linear infinite';

            if (!isManualRefresh && !lastStatsData) {
                document.getElementById('stats-content').innerHTML = `

                    <div style="text-align:center; padding:50px 20px;">

                        <div class="loader-small" style="margin:auto; width:36px; height:36px;"></div>

                        <p style="color:#8e8e93; margin-top:14px; font-size:13px;">Obteniendo telemetría en tiempo real...</p>

                    </div>`;
            }

            try {
                const res = await fetch('/api/stats');
                const data = await res.json();

                lastStatsData = data;

                renderStatsContent(data);

                // Auto-poll if assistant is active or running

                const asst = data.assistant || {};

                if (asst.active || asst.status === 'running') {
                    if (!statsPollInterval) {
                        statsPollInterval = setInterval(async () => {
                            const m = document.getElementById('stats-modal');

                            if (!m || m.style.display === 'none') {
                                clearInterval(statsPollInterval);

                                statsPollInterval = null;

                                return;
                            }

                            try {
                                const r = await fetch('/api/stats');
                                const d = await r.json();

                                lastStatsData = d;

                                renderStatsContent(d);
                            } catch (e) {}
                        }, 2500);
                    }
                } else if (statsPollInterval) {
                    clearInterval(statsPollInterval);

                    statsPollInterval = null;
                }
            } catch (err) {
                document.getElementById('stats-content').innerHTML = `<p style="color:#ff453a; text-align:center; padding:30px;">Error al cargar estadísticas: ${err.message}</p>`;
            } finally {
                if (refreshIcon) refreshIcon.style.animation = 'none';
            }
        };

        function renderStatsBreakdownList(breakdown, filter = '') {
            const entries = Object.entries(breakdown);

            if (!entries.length) return '<div style="color:#8e8e93; text-align:center; padding:15px;">No hay álbumes para mostrar</div>';

            const maxCount = entries[0][1] || 1;
            const q = filter.trim().toLowerCase();
            const filtered = q ? entries.filter(([name]) => name.toLowerCase().includes(q)) : entries;

            if (!filtered.length) {
                return `<div style="color:#8e8e93; text-align:center; padding:15px;">No se encontraron álbumes que coincidan con "${filter}"</div>`;
            }

            return filtered.map(([name, count]) => {
                const pct = Math.round((count / maxCount) * 100);

                return `

                    <div class="stats-album-item" style="display:flex; align-items:center; justify-content:space-between; padding:6px 8px; border-radius:8px; margin-bottom:4px; background:rgba(255,255,255,0.02); transition:background 0.15s;" onmouseover="this.style.background='rgba(255,255,255,0.06)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">

                        <div style="flex:1; min-width:0; margin-right:12px;">

                            <div style="font-size:13px; font-weight:600; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${name}</div>

                            <div style="width:100%; height:4px; background:rgba(255,255,255,0.06); border-radius:2px; margin-top:4px; overflow:hidden;">

                                <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, #0a84ff, #bf5af2); border-radius:2px;"></div>

                            </div>

                        </div>

                        <div style="font-size:12px; font-weight:700; color:#8e8e93; font-feature-settings:'tnum'; flex-shrink:0;">

                            ${count.toLocaleString()}

                        </div>

                    </div>

                `;
            }).join('');
        }

        window.filterStatsList = function(q) {
            const listEl = document.getElementById('stats-album-list');

            if (!listEl || !lastStatsData) return;

            listEl.innerHTML = renderStatsBreakdownList(lastStatsData.breakdown || {}, q);
        };

        function renderStatsContent(data) {
            const asst = data.assistant || {};
            const totalGallery = data.total || 0;
            const classified = data.clasificadas || 0;
            const manualUser = data.manual_user || 0;
            const iaVerified = data.ia_verified || 0;
            const dudosos = data.dudosos || 0;
            const pendientes = data.pendientes || 0;
            const pctGlobal = totalGallery > 0 ? Math.round((classified / totalGallery) * 100) : 0;
            const asstStatus = asst.status || 'completed';
            const isAsstRunning = asst.active || asstStatus === 'running';
            const asstTotal = asst.total || 0;
            const asstProc = asst.processed || 0;
            const asstRem = asst.remaining !== undefined ? asst.remaining : Math.max(0, asstTotal - asstProc);
            const asstPct = asst.percentage || (asstTotal > 0 ? Math.round((asstProc / asstTotal) * 100) : 100);
            const asstRate = asst.rate || 0;
            const asstEta = asst.eta_formatted || (asstRem === 0 ? 'Completado' : (asst.eta_minutes ? `~${Math.round(asst.eta_minutes)} min` : 'Calculando...'));
            const cloudPlaceholders = asst.cloud_placeholders || 0;
            const totalAppleOrganized = asst.total_apple_db || data.iphone_clasificadas || 0;
            const html = `

                <!-- HERO CARD: ASISTENTE AUTÓNOMO EN SEGUNDO PLANO -->

                <div style="background: linear-gradient(135deg, rgba(10,132,255,0.1) 0%, rgba(191,90,242,0.1) 100%); border: 1px solid rgba(10,132,255,0.3); border-radius: 18px; padding: 20px; margin-bottom: 22px; position: relative; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">

                        <div style="display:flex; align-items:center; gap:8px;">

                            <div style="width:32px; height:32px; border-radius:8px; background:linear-gradient(135deg, #0a84ff, #bf5af2); display:flex; align-items:center; justify-content:center; font-size:16px;">⚡</div>

                            <div>

                                <div style="font-size:14px; font-weight:800; color:#fff;">Asistente Autónomo (iCloud & Aprendizaje)</div>

                                <div style="font-size:11px; color:#8e8e93;">Organización facial en segundo plano y extracción de características</div>

                            </div>

                        </div>

                        <div>

                            ${isAsstRunning ? `

                                <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(48,209,88,0.15); border:1px solid rgba(48,209,88,0.4); padding:4px 10px; border-radius:14px; font-size:11px; font-weight:700; color:#30d158;">

                                    <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#30d158; box-shadow:0 0 8px #30d158; animation:pulse-glow 1.5s infinite;"></span>

                                    ANALIZANDO EN TIEMPO REAL

                                </div>

                            ` : `

                                <div style="display:inline-flex; align-items:center; gap:6px; background:rgba(100,210,255,0.12); border:1px solid rgba(100,210,255,0.3); padding:4px 10px; border-radius:14px; font-size:11px; font-weight:700; color:#64d2ff;">

                                    <span>✓</span> TODO ORGANIZADO

                                </div>

                            `}

                        </div>

                    </div>

                    <!-- Progress Bar & Big Counter -->

                    <div style="margin-bottom:16px;">

                        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px;">

                            <div>

                                <span style="font-size:26px; font-weight:900; letter-spacing:-0.5px; color:#fff; font-feature-settings:'tnum';">${asstProc.toLocaleString()}</span>

                                <span style="font-size:14px; color:#8e8e93; font-weight:600;"> / ${asstTotal.toLocaleString()} fotos del lote</span>

                            </div>

                            <div style="text-align:right;">

                                <span style="font-size:16px; font-weight:800; color:#64d2ff;">${asstPct}%</span>

                                <span style="font-size:11px; color:#8e8e93; margin-left:6px;">(${asstRem.toLocaleString()} restantes)</span>

                            </div>

                        </div>

                        <div style="width:100%; height:12px; background:rgba(255,255,255,0.08); border-radius:10px; overflow:hidden; position:relative; padding:1px;">

                            <div style="width:${Math.min(100, asstPct)}%; height:100%; border-radius:8px; background:linear-gradient(90deg, #0a84ff 0%, #bf5af2 50%, #30d158 100%); transition:width 0.6s cubic-bezier(0.16, 1, 0.3, 1); box-shadow:0 0 12px rgba(10,132,255,0.6);"></div>

                        </div>

                    </div>

                    <!-- 4 Assistant Telemetry Tiles -->

                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:10px; margin-bottom:14px;">

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Velocidad</div>

                            <div style="font-size:18px; font-weight:800; color:#64d2ff; margin-top:2px;">${asstRate} <span style="font-size:11px; font-weight:500;">img/s</span></div>

                        </div>

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Tiempo Restante</div>

                            <div style="font-size:18px; font-weight:800; color:#ffd60a; margin-top:2px;">${asstEta}</div>

                        </div>

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">Total Apple en Álbumes</div>

                            <div style="font-size:18px; font-weight:800; color:#30d158; margin-top:2px;">${totalAppleOrganized.toLocaleString()}</div>

                        </div>

                        <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07); padding:10px; border-radius:12px; text-align:center;">

                            <div style="font-size:10px; color:#8e8e93; font-weight:700; text-transform:uppercase;">iCloud en la Nube</div>

                            <div style="font-size:18px; font-weight:800; color:#bf5af2; margin-top:2px;" title="Pendientes de sincronización local por iCloud para Windows">${cloudPlaceholders.toLocaleString()}</div>

                        </div>

                    </div>

                    <!-- Assistant Breakdown Tags -->

                    <div style="display:flex; flex-wrap:wrap; gap:6px; font-size:11px;">

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">👤 YO: <strong>${asst.yo || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">🏷️ Conocidas: <strong>${asst.known_persons || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">📸 Capturas: <strong>${asst.capturas || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">🌄 Sin Rostro: <strong>${asst.sin_rostro || 0}</strong></span>

                        <span style="background:rgba(255,255,255,0.06); padding:4px 8px; border-radius:8px; color:#e5e5ea;">❓ Desconocidos: <strong>${asst.desconocidos || 0}</strong></span>

                        ${asst.errors ? `<span style="background:rgba(255,69,58,0.15); border:1px solid rgba(255,69,58,0.3); padding:4px 8px; border-radius:8px; color:#ff453a;">⚠️ Errores: <strong>${asst.errors}</strong></span>` : ''}

                    </div>

                </div>

                <!-- SECCIÓN 2: ESTADO GLOBAL DE LA FOTOTECA -->

                <div style="margin-bottom:22px;">

                    <div style="font-size:12px; font-weight:700; color:#8e8e93; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;">

                        Estado Global de la Galería

                    </div>

                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px; margin-bottom:14px;">

                        <!-- Total -->

                        <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); padding:14px; border-radius:14px;">

                            <div style="font-size:11px; color:#8e8e93; font-weight:600;">Total Elementos</div>

                            <div style="font-size:24px; font-weight:800; color:#fff; margin-top:2px;">${totalGallery.toLocaleString()}</div>

                            <div style="font-size:11px; color:#64d2ff; margin-top:4px;">${pctGlobal}% clasificado</div>

                        </div>

                        <!-- Manual User -->

                        <div style="background:rgba(48,209,88,0.06); border:1px solid rgba(48,209,88,0.2); padding:14px; border-radius:14px;">

                            <div style="display:flex; justify-content:space-between; align-items:center;">

                                <span style="font-size:11px; color:#30d158; font-weight:600;">✏️ Confirmadas por Mí</span>

                                <span style="font-size:9px; background:rgba(48,209,88,0.2); color:#30d158; padding:1px 5px; border-radius:4px; font-weight:700;">100% Certeza</span>

                            </div>

                            <div style="font-size:24px; font-weight:800; color:#30d158; margin-top:2px;">${manualUser.toLocaleString()}</div>

                            <div style="font-size:11px; color:rgba(48,209,88,0.8); margin-top:4px;">Centroides anclados</div>

                        </div>

                        <!-- IA Verified -->

                        <div style="background:rgba(10,132,255,0.06); border:1px solid rgba(10,132,255,0.2); padding:14px; border-radius:14px;">

                            <div style="display:flex; justify-content:space-between; align-items:center;">

                                <span style="font-size:11px; color:#0a84ff; font-weight:600;">✨ Validadas por IA</span>

                                <span style="font-size:9px; background:rgba(10,132,255,0.2); color:#0a84ff; padding:1px 5px; border-radius:4px; font-weight:700;">Alta Confianza</span>

                            </div>

                            <div style="font-size:24px; font-weight:800; color:#0a84ff; margin-top:2px;">${iaVerified.toLocaleString()}</div>

                            <div style="font-size:11px; color:rgba(10,132,255,0.8); margin-top:4px;">Reconocimiento SFace</div>

                        </div>

                        <!-- Pendientes / Dudosas -->

                        <div style="background:rgba(255,159,10,0.06); border:1px solid rgba(255,159,10,0.2); padding:14px; border-radius:14px;">

                            <div style="display:flex; justify-content:space-between; align-items:center;">

                                <span style="font-size:11px; color:#ff9f0a; font-weight:600;">⚠️ Por Revisar</span>

                                <span style="font-size:9px; background:rgba(255,159,10,0.2); color:#ff9f0a; padding:1px 5px; border-radius:4px; font-weight:700;">Dudosas + Nuevas</span>

                            </div>

                            <div style="font-size:24px; font-weight:800; color:#ff9f0a; margin-top:2px;">${(dudosos + pendientes).toLocaleString()}</div>

                            <div style="font-size:11px; color:rgba(255,159,10,0.8); margin-top:4px;">${dudosos} dudosas / ${pendientes} pendientes</div>

                        </div>

                    </div>

                    <!-- Segmented Progress Bar -->

                    <div style="margin-bottom:12px;">

                        <div style="width:100%; height:10px; background:rgba(255,255,255,0.08); border-radius:8px; overflow:hidden; display:flex;">

                            <div style="width:${totalGallery > 0 ? (manualUser / totalGallery * 100) : 0}%; background:#30d158;" title="Manuales: ${manualUser}"></div>

                            <div style="width:${totalGallery > 0 ? (iaVerified / totalGallery * 100) : 0}%; background:#0a84ff;" title="IA: ${iaVerified}"></div>

                            <div style="width:${totalGallery > 0 ? (dudosos / totalGallery * 100) : 0}%; background:#ff9f0a;" title="Dudosas: ${dudosos}"></div>

                            <div style="width:${totalGallery > 0 ? (pendientes / totalGallery * 100) : 0}%; background:#ff453a;" title="Pendientes: ${pendientes}"></div>

                        </div>

                    </div>

                    <!-- Device Origin Badges -->

                    <div style="display:flex; gap:10px; flex-wrap:wrap;">

                        <div style="flex:1; min-width:200px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); padding:10px 14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">

                            <div style="display:flex; align-items:center; gap:8px;">

                                <span style="font-size:16px;">🍎</span>

                                <div>

                                    <div style="font-size:12px; font-weight:700; color:#fff;">Apple iPhone / iCloud</div>

                                    <div style="font-size:10px; color:#8e8e93;">${(data.iphone_clasificadas || 0).toLocaleString()} organizadas</div>

                                </div>

                            </div>

                            <div style="font-size:14px; font-weight:800; color:#fff;">${(data.iphone_total || 0).toLocaleString()}</div>

                        </div>

                        <div style="flex:1; min-width:200px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); padding:10px 14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center;">

                            <div style="display:flex; align-items:center; gap:8px;">

                                <span style="font-size:16px;">🤖</span>

                                <div>

                                    <div style="font-size:12px; font-weight:700; color:#fff;">Android & Otras Fuentes</div>

                                    <div style="font-size:10px; color:#8e8e93;">${(data.android_clasificadas || 0).toLocaleString()} organizadas</div>

                                </div>

                            </div>

                            <div style="font-size:14px; font-weight:800; color:#fff;">${(data.android_total || 0).toLocaleString()}</div>

                        </div>

                    </div>

                </div>

                <!-- SECCIÓN 3: DESGLOSE POR ÁLBUM / PERSONA (CON BUSCADOR) -->

                <div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;">

                        <div style="font-size:12px; font-weight:700; color:#8e8e93; text-transform:uppercase; letter-spacing:0.5px;">

                            Distribución por Álbum y Persona (${Object.keys(data.breakdown || {}).length} álbumes)

                        </div>

                        <div style="position:relative; width:220px;">

                            <input type="text" id="stats-filter-input" placeholder="🔍 Filtrar álbum..." oninput="filterStatsList(this.value)" style="width:100%; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); padding:5px 10px; border-radius:8px; color:#fff; font-size:12px; outline:none; transition:border-color 0.2s;" onfocus="this.style.borderColor='#0a84ff'" onblur="this.style.borderColor='rgba(255,255,255,0.12)'">

                        </div>

                    </div>

                    <div id="stats-album-list" style="max-height: 280px; overflow-y: auto; padding-right: 6px;" class="custom-scrollbar">

                        ${renderStatsBreakdownList(data.breakdown || {})}

                    </div>

                </div>

            `;

            document.getElementById('stats-content').innerHTML = html;
        }

        async function forceReanalyze() {
            if (!confirm("¿Seguro que quieres forzar un re-análisis? Esto borrará la caché y tardará unos segundos, pero la IA usará su conocimiento actualizado para puntuar las caras.")) return;

            const btn = document.getElementById('btn-reanalyze');

            btn.style.opacity = '0.5';

            btn.textContent = 'Recalculando...';

            btn.style.pointerEvents = 'none';

            try {
                await fetch('/api/clear_confidence_cache', {method: 'POST'});

                await openIntelligentCleanup();
            } catch(e) {
                console.error(e);

                showToast("Error al re-analizar", true);
            }
        }

        let smartCleanInterval;

async function runAnalysis(force=false) {
            if (!currentFileObj) return;

            const currentRunPath = currentFileObj.path;
            const container = document.getElementById('lb-media-container');
            const mediaEl = container ? container.querySelector('.lb-media-element') : null;

            if (isCurrentVideo && mediaEl && !mediaEl.paused) {
                mediaEl.pause();
            }

            document.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());

            const cardsContainer = document.getElementById('person-cards-container');

            if (cardsContainer && force) {
                cardsContainer.innerHTML = '<div id="lb-faces-loading-state" style="padding:24px 16px; text-align:center; color:#8e8e93;"><div class="loader-small" style="margin:0 auto 10px auto;"></div><div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">Escaneando caras...</div></div>';
            }

            // Safety watchdog timer (3 seconds max before displaying helper state)

            const loadingWatchdog = setTimeout(() => {
                const loadingEl = document.getElementById('lb-faces-loading-state');

                if (loadingEl && cardsContainer && currentFileObj && currentFileObj.path === currentRunPath) {
                    cardsContainer.innerHTML = `

                        <div style="padding:22px 16px; text-align:center; color:#8e8e93;">

                            <div style="font-size:24px; margin-bottom:6px;">⏳</div>

                            <div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">Detección en curso...</div>

                            <div style="font-size:11px; margin-bottom:12px;">El análisis está tomando unos segundos más.</div>

                            <button onclick="runAnalysis(true)" style="padding:6px 14px; border-radius:10px; background:rgba(10,132,255,0.15); border:1px solid rgba(10,132,255,0.3); color:#64d2ff; font-size:11px; font-weight:600; cursor:pointer;">🔄 Reintentar detección</button>

                        </div>`;
                }
            }, 3000);

            let timestamp = isCurrentVideo && mediaEl ? mediaEl.currentTime : null;
            let data;
            const abortCtrl = new AbortController();
            const abortTimer = setTimeout(() => abortCtrl.abort(), 30000);

            try {
                const res = await fetch('/api/analyze', {
                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({
                        path: currentFileObj.path,

                        timestamp: timestamp,

                        force: Boolean(force),

                        current_cat: typeof currentCat !== 'undefined' ? currentCat : null,

                        current_ident: typeof currentIdent !== 'undefined' ? currentIdent : null
                    }),

                    signal: abortCtrl.signal
                });

                clearTimeout(abortTimer);

                clearTimeout(loadingWatchdog);

                if (!res.ok) {
                    throw new Error(`Server returned ${res.status}`);
                }

                data = await res.json();
            } catch (err) {
                clearTimeout(abortTimer);

                clearTimeout(loadingWatchdog);

                console.error(err);

                if (cardsContainer && currentFileObj && currentFileObj.path === currentRunPath) {
                    cardsContainer.innerHTML = `

                        <div style="padding:22px 16px; text-align:center; color:#ff9f0a;">

                            <div style="font-size:24px; margin-bottom:6px;">⚠️</div>

                            <div style="font-size:12px; font-weight:600; color:#fff; margin-bottom:4px;">No se pudo completar el análisis</div>

                            <div style="font-size:11px; margin-bottom:12px; color:#8e8e93;">El servidor tardó en responder.</div>

                            <button onclick="runAnalysis(true)" style="padding:6px 14px; border-radius:10px; background:rgba(10,132,255,0.2); border:1px solid #0a84ff; color:#0a84ff; font-size:11px; font-weight:600; cursor:pointer;">🔄 Reintentar detección</button>

                        </div>`;
                }

                return;
            }

            if (!currentFileObj || currentFileObj.path !== currentRunPath) return; cardsContainer.innerHTML = '';

            currentFaces = data.faces || [];

            const detectedCount = currentFaces.length;
            const mobileCountEl = document.getElementById('mobile-faces-count');

            if (mobileCountEl) mobileCountEl.textContent = detectedCount;

            const mobilePill = document.getElementById('mobile-lb-sheet-pill');

            if (mobilePill) mobilePill.innerHTML = `▲ 👥 Caras (<span id="mobile-faces-count">${detectedCount}</span>)`;

            const topBtnLabel = document.querySelector('#btn-toggle-lb-panel .lb-btn-label');

            if (topBtnLabel) topBtnLabel.textContent = `Caras (${detectedCount})`;

            const isPerson = typeof isPersonAlbum === 'function' ? isPersonAlbum(currentCat, currentIdent) : false;
            const hasManualEdit = Boolean(
                (currentFileObj && (currentFileObj.is_manual || (currentFileObj.source && currentFileObj.source.includes('Manual')))) ||
                (data && data.faces && data.faces.some(f => f.is_manual || (f.identity === currentIdent && f.confidence >= 0.99)))
            );

            if (isPerson && !isSystemFolder && !hasManualEdit && currentFileObj && (currentFileObj.is_dudoso || currentFileObj.status === 'Dudoso' || currentFileObj.album_section === 'review' || (currentFileObj.source && currentFileObj.source.includes('Por Confirmar')))) {
                const dudosoBanner = document.createElement('div');

                dudosoBanner.id = 'lightbox-dudoso-banner';

                dudosoBanner.style.cssText = 'background:rgba(255,159,10,0.15); border:1px solid #ff9f0a; border-radius:10px; padding:10px; margin-bottom:12px; text-align:center;';

                dudosoBanner.innerHTML = `

                    <div style="font-weight:700; color:#ff9f0a; font-size:12px; margin-bottom:4px;">⚠️ FOTO POR CONFIRMAR</div>

                    <div style="font-size:11px; color:#fff; margin-bottom:8px;">¿Confirmas que esta foto pertenece a <b>${currentIdent}</b>?</div>

                    <div style="display:flex; gap:6px;">

                        <button onclick="confirmDudosoPhoto(true)" style="flex:1; padding:7px 4px; border-radius:7px; border:1px solid #30d158; background:rgba(48,209,88,0.2); color:#30d158; font-weight:700; font-size:11px; cursor:pointer;">✅ Sí, confirmar</button>

                        <button onclick="confirmDudosoPhoto(false)" style="flex:1; padding:7px 4px; border-radius:7px; border:1px solid #ff453a; background:rgba(255,69,58,0.2); color:#ff6961; font-weight:700; font-size:11px; cursor:pointer;">❌ No es ${currentIdent}</button>

                    </div>

                `;

                cardsContainer.appendChild(dudosoBanner);
            }

            if (data.faces && data.faces.length > 0) {
                let intrinsicWidth = isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth;
                let intrinsicHeight = isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight;

                if (!intrinsicWidth && data.faces.length > 0) {
                    intrinsicWidth = data.faces[0].img_width;

                    intrinsicHeight = data.faces[0].img_height;
                }

                // Sincronizar tamaño del contenedor con el tamaño real de la imagen renderizada

                resizeContainerToImage();

                let hasUnconfirmed = false;

                document.querySelectorAll('.lb-bounding-box').forEach(b => b.remove());
                data.faces.forEach((face, idx) => {
                    if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) hasUnconfirmed = true;

                    createFaceElements(face, idx + 1, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);
                });

                const btnIgnore = document.getElementById('btn-ignore-unconfirmed');

                if (btnIgnore) {
                    if (hasUnconfirmed) {
                        btnIgnore.style.display = 'block';

                        btnIgnore.textContent = "🗑️ Ignorar caras no confirmadas";

                        btnIgnore.style.opacity = '1';

                        btnIgnore.style.pointerEvents = 'auto';
                    } else {
                        btnIgnore.style.display = 'none';
                    }
                }
            } else {
                cardsContainer.innerHTML = `

                    <div style="padding:28px 16px; text-align:center; color:#8e8e93;">

                        <div style="font-size:28px; margin-bottom:8px; opacity:0.6;">📷</div>

                        <div style="font-size:13px; font-weight:600; color:#fff; margin-bottom:4px;">Sin personas detectadas</div>

                        <div style="font-size:11px; line-height:1.4;">No se encontraron caras registradas en esta imagen.</div>

                        <button onclick="runAnalysis(true)" style="margin-top:14px; padding:6px 14px; border-radius:12px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); color:#64d2ff; font-size:11px; font-weight:600; cursor:pointer;">🔍 Escanear de nuevo</button>

                    </div>`;
            }
        }

                function highlightFace(faceNum) {
            document.querySelectorAll('.lb-bounding-box').forEach(b => {
                b.style.borderColor = 'rgba(255, 255, 255, 0.4)';

                b.style.zIndex = '1';

                b.classList.remove('active');
            });

            document.querySelectorAll('.person-card').forEach(c => c.style.background = 'rgba(28, 28, 30, 0.5)');

            const box = document.getElementById(`bbox-${faceNum}`);

            if (box) {
                box.style.borderColor = '#0a84ff';

                box.style.zIndex = '10';

                box.classList.add('active');

                // Auto-Focus Zoom

                const mediaEl = document.getElementById('lb-media');

                if (mediaEl && box.dataset.faceX) {
                    const intrinsicWidth = mediaEl.naturalWidth || mediaEl.videoWidth;
                    const intrinsicHeight = mediaEl.naturalHeight || mediaEl.videoHeight;

                    if (intrinsicWidth && intrinsicHeight) {
                        const fx = parseFloat(box.dataset.faceX);
                        const fy = parseFloat(box.dataset.faceY);
                        const fw = parseFloat(box.dataset.faceW);
                        const fh = parseFloat(box.dataset.faceH);
                        const centerX = fx + (fw / 2);
                        const centerY = fy + (fh / 2);
                        const renderScale = mediaEl.clientWidth / intrinsicWidth;
                        const offX = centerX - (intrinsicWidth / 2);
                        const offY = centerY - (intrinsicHeight / 2);

                        if (window.innerWidth > 820) {
                            if (zoomLevel < 1.3) {
                                zoomLevel = 1.3;

                                panX = -(offX * renderScale) * zoomLevel;

                                panY = -(offY * renderScale) * zoomLevel;

                                applyZoomTransform();
                            }
                        }
                    }
                }
            }

            const card = document.getElementById("person-card-" + faceNum) || document.getElementById("pcard-" + faceNum);

            if (card) {
                card.style.background = 'rgba(10, 132, 255, 0.2)';

                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

            if (window.innerWidth <= 820 && typeof toggleMobileLightboxSheet === 'function') {
                toggleMobileLightboxSheet(true);
            }
        }

        document.addEventListener('keydown', (e) => {
            // No actuar si estamos escribiendo en un input

            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

            if (e.key === 'Delete' || e.key === 'Backspace') {
                const activeBox = document.querySelector('.lb-bounding-box.active');

                if (activeBox && currentFileObj) {
                    const faceNum = activeBox.id.replace('bbox-', '');
                    const falsePosId = JSON.stringify({categoria: 'Ignorar', identidad: 'Falso_Positivo'});
                    const fx = parseFloat(activeBox.dataset.faceX) || 0;
                    const fy = parseFloat(activeBox.dataset.faceY) || 0;
                    const fw = parseFloat(activeBox.dataset.faceW) || 100;
                    const fh = parseFloat(activeBox.dataset.faceH) || 100;

                    inlineCorrect(
                        encodeURIComponent(currentFileObj.path),

                        falsePosId,

                        faceNum,

                        fx, fy, fw, fh
                    );
                }
            }
        });

        function createFaceElements(face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer) {
            intrinsicWidth = intrinsicWidth || (mediaEl ? mediaEl.naturalWidth || mediaEl.clientWidth : 800) || 800;

            intrinsicHeight = intrinsicHeight || (mediaEl ? mediaEl.naturalHeight || mediaEl.clientHeight : 600) || 600;

            // 1. Bounding Box sobre la Foto (Movible y Redimensionable)

            const existingBox = document.getElementById(`bbox-${faceNum}`);
            if (existingBox) existingBox.remove();
            const box = document.createElement('div');

            box.className = 'lb-bounding-box';

            box.id = `bbox-${faceNum}`;

            // Atributos de datos para el atajo de teclado

            box.dataset.faceX = face.x;

            box.dataset.faceY = face.y;

            box.dataset.faceW = face.width;

            box.dataset.faceH = face.height;

            const percX = (face.x / intrinsicWidth) * 100;
            const percY = (face.y / intrinsicHeight) * 100;
            const percW = (face.width / intrinsicWidth) * 100;
            const percH = (face.height / intrinsicHeight) * 100;

            box.style.left = `${percX}%`;

            box.style.top = `${percY}%`;

            box.style.width = `${percW}%`;

            box.style.height = `${percH}%`;

            const badge = document.createElement('div');

            badge.className = 'lb-bb-badge';

            badge.textContent = `#${faceNum}`;

            box.appendChild(badge);

            ['tl', 'tr', 'bl', 'br', 't', 'b', 'l', 'r'].forEach(corner => {
                const handle = document.createElement('div');

                handle.className = `resize-handle handle-${corner}`;

                handle.dataset.corner = corner;

                box.appendChild(handle);
            });

            box.onclick = (e) => {
                if (box.dataset.wasDragged === 'true') {
                    box.dataset.wasDragged = 'false';

                    return;
                }

                if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;

                e.stopPropagation();

                // Toggle selection visual

                document.querySelectorAll('.lb-box.selected').forEach(b => b.classList.remove('selected'));

                box.classList.add('selected');

                // Store selected box ID globally

                window.selectedBoxId = box.id;

                highlightFace(faceNum);

                // En movil: abrir directamente la barra inferior nativa y hacer scroll a la cara (cero popups gigantes sobre la imagen)

                if (window.innerWidth <= 820) {
                    if (typeof toggleMobileLightboxSheet === 'function') {
                        toggleMobileLightboxSheet(true);
                    }

                    const pcard = document.getElementById("pcard-" + faceNum) || document.getElementById("person-card-" + faceNum);

                    if (pcard) {
                        pcard.scrollIntoView({ behavior: 'smooth', block: 'center' });

                        pcard.style.transition = 'all 0.3s ease';

                        pcard.style.background = 'rgba(10, 132, 255, 0.25)';

                        pcard.style.borderColor = '#0a84ff';

                        setTimeout(() => {
                            pcard.style.background = '';

                            pcard.style.borderColor = '';
                        }, 1500);
                    }

                    return;
                }

                // En escritorio: contra-escalar el menu popup para que SIEMPRE mida 220px exactos independientemente del zoom

                let existingMenu = box.querySelector('.lb-box-popup');

                if (existingMenu) {
                    existingMenu.remove();

                    return;
                }

                document.querySelectorAll('.lb-box-popup').forEach(m => m.remove());

                const curZoom = zoomLevel || 1.0;
                const popup = document.createElement('div');

                popup.className = 'lb-box-popup';

                popup.style.cssText = 'position:absolute; bottom:-65px; left:50%; transform:translateX(-50%) scale(' + (1 / curZoom) + '); transform-origin:top center; z-index:100; background:rgba(20,20,22,0.95); backdrop-filter:blur(20px); padding:8px; border-radius:12px; border:1px solid rgba(255,255,255,0.25); box-shadow:0 8px 30px rgba(0,0,0,0.6); display:flex; flex-direction:column; gap:6px; width:220px; max-width:240px; font-size:11px;';

                let pathParts1 = currentFileObj.path.split(/[\\/]/);
                let folderName = pathParts1.slice(-2, -1)[0];
                let categoryName = pathParts1.slice(-3, -2)[0];

                if (folderName === '_Dudosos') {
                    folderName = pathParts1.slice(-3, -2)[0];

                    categoryName = pathParts1.slice(-4, -3)[0];
                }

                let rejectedId = JSON.stringify({categoria: '_Dudosos', identidad: 'Desconocido'});
                let innerHtml = `

                    <div style="color:white; font-size:0.75rem; text-align:center; opacity:0.7; padding-bottom:4px; border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:4px;">Face #${faceNum}</div>

                `;

                innerHtml += generateReassignHTML(face, faceNum, 'quickReassignFace', 'popup');

            popup.innerHTML = innerHtml;

            box.appendChild(popup);
        };

            // Hacer la caja arrastrable y redimensionable

            makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl);

            container.appendChild(box);

            // 2. Avatar Recortado en Canvas

            let avatarUrl = updateAvatarCrop(mediaEl, face);

            // 3. Tarjeta en Sidebar

            const card = document.createElement('div');

            card.className = 'person-card';

            card.id = `pcard-${faceNum}`;

            let folderName, categoryName;

            if (currentCat && currentCat !== 'Resultados' && currentCat !== 'Personas Sin Nombre' && currentCat !== 'Limpieza Inteligente') {
                categoryName = currentCat;

                folderName = currentIdent;
            } else {
                let pathParts2 = currentFileObj.path.split(/[\\/]/);

                folderName = pathParts2.slice(-2, -1)[0];

                categoryName = pathParts2.slice(-3, -2)[0];

                if (folderName === '_Dudosos') {
                    folderName = pathParts2.slice(-3, -2)[0];

                    categoryName = pathParts2.slice(-4, -3)[0];
                }
            }

            // Determinar si hay sugerencia IA para mostrar en la tarjeta (con exclusión mutua estricta)

            const isGroupOrCategory = isInvalidFolderName(folderName) || !Boolean(folderName.match(/^[CFPM]\.?\s+/i) || folderName === 'YO' || (typeof identitiesList !== 'undefined' && identitiesList.some(id => id.identidad === folderName)));
            const cleanFaceId = face.identity ? face.identity.replace(/^\?\s*/, '').trim() : '';
            let isAlbumOwner = !isGroupOrCategory && (face.identity === folderName || face.tag_type === 'album_owner' || (cleanFaceId === folderName && !ownerClaimedOnOtherFace));
            let isDoubtfulOwner = !isGroupOrCategory && (face.identity && face.identity.startsWith('? ') && face.identity.replace(/^\?\s*/, '').trim() === folderName);
            const otherClaimedInCard = new Set();
            let ownerClaimedOnOtherFace = false;

            if (typeof currentFaces !== 'undefined' && Array.isArray(currentFaces)) {
                currentFaces.forEach((f, idx) => {
                    if (idx !== faceNum - 1) {
                        const rawId = f.identity || '';
                        const cleanId = rawId.replace(/^\?\s*/, '').trim();
                        const isNonPerson = !cleanId || cleanId === 'Desconocido' || cleanId.startsWith('IA ') || cleanId.startsWith('Falso_') || cleanId.startsWith('Ignorar_') || cleanId.includes('(Sin rostro') || cleanId.toLowerCase().includes('desconocid');

                        if (!isNonPerson) {
                            otherClaimedInCard.add(cleanId);

                            otherClaimedInCard.add(rawId);

                            if (cleanId === folderName || rawId === folderName || f.tag_type === 'dataset' || f.is_owner || f.is_centroid) {
                                ownerClaimedOnOtherFace = true;

                                if (folderName) otherClaimedInCard.add(folderName);
                            }
                        }

                        if (f.is_manual && cleanId) {
                            otherClaimedInCard.add(cleanId);

                            if (cleanId === folderName) {
                                ownerClaimedOnOtherFace = true;

                                if (folderName) otherClaimedInCard.add(folderName);
                            }
                        }
                    }
                });
            }

            // Si el dueño del álbum ya está identificado en otra cara de la misma foto, esta cara no es el dueño

            if (ownerClaimedOnOtherFace) {
                isAlbumOwner = false;

                isDoubtfulOwner = false;
            }

            // Extract AI suggestion if present (never display 'Desconocido' if an AI suggestion or candidate exists!)

            let rawSuggested = face.suggested_identity;

            if (!rawSuggested && face.identity) {
                if (face.identity.startsWith('? ')) {
                    rawSuggested = face.identity.replace(/^\?\s*/, '').trim();
                } else if (face.identity.startsWith('IA (Pendiente): ')) {
                    rawSuggested = face.identity.replace('IA (Pendiente): ', '').trim();
                } else if (face.identity.startsWith('IA: ')) {
                    rawSuggested = face.identity.replace('IA: ', '').trim();
                }
            }

            if (!rawSuggested && isDoubtfulOwner && face.identity) {
                rawSuggested = face.identity.replace(/^\?\s*/, '').trim();
            }

            if (rawSuggested && (otherClaimedInCard.has(rawSuggested) || (rawSuggested === folderName && ownerClaimedOnOtherFace))) {
                rawSuggested = null;
            }

            const cardSuggested = rawSuggested;
            const hasAiSugg = Boolean(cardSuggested && cardSuggested !== folderName && !otherClaimedInCard.has(cardSuggested));

            // Face Title display: If face has an AI suggestion, show the suggested name! NEVER just 'Desconocido'

            let rawIdent = face.identity || '';

            if (rawIdent.startsWith('? ') && !rawIdent.startsWith('? Desconocido')) {
                rawIdent = rawIdent.replace(/^\?\s*/, '').trim();
            }

            const hasSuggCandidate = Boolean(cardSuggested || face.suggested_identity || (face.identity && (face.identity.startsWith('? ') || face.identity.startsWith('IA (Pendiente)'))));

            if (!rawIdent || rawIdent === 'Desconocido' || rawIdent.startsWith('IA (Pendiente)') || rawIdent.startsWith('? Desconocido') || rawIdent === '?') {
                if (cardSuggested) rawIdent = cardSuggested;
                else if (face.suggested_identity) rawIdent = face.suggested_identity;
                else rawIdent = 'Desconocido';
            }

            const cleanIdent = rawIdent.replace(/^\?\s*/, '').replace(/^IA\s*\(Pendiente\):\s*/i, '').replace(/^IA:\s*/i, '').trim();
            const isSuggBadge = hasAiSugg || isDoubtfulOwner || face.tag_type === 'ai_suggestion' || (face.confidence && String(face.confidence).includes('Sugerencia')) || hasSuggCandidate;
            let displayTitle = cleanIdent || 'Desconocido';

            if (displayTitle !== 'Desconocido' && isSuggBadge && !isAlbumOwner && !displayTitle.includes('(Sugerencia)')) {
                displayTitle += ' (Sugerencia)';
            }

            let confBadge = '';

            if (isAlbumOwner || face.tag_type === 'album_owner') {
                confBadge = `<span style="font-size:10px; color:#30d158; background:rgba(48,209,88,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">👑 Dueño del álbum</span>`;
            } else if (face.confidence && String(face.confidence).includes('Manual')) {
                confBadge = `<span style="font-size:10px; color:#ff9f0a; background:rgba(255,159,10,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">✏️ Editado</span>`;
            } else if (face.tag_type === 'dataset') {
                confBadge = `<span style="font-size:10px; color:#64d2ff; background:rgba(10,132,255,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">🏷️ Dataset</span>`;
            } else if (isDoubtfulOwner || (face.confidence && String(face.confidence).includes('Dudoso'))) {
                confBadge = `<span style="font-size:10px; color:#ff9f0a; background:rgba(255,159,10,0.15); padding:2px 7px; border-radius:8px; font-weight:700;">⚠️ Por Confirmar</span>`;
            } else if (isSuggBadge) {
                const suggPct = face.suggested_score ? ` (${Math.round(face.suggested_score * 100)}%)` : '';

                confBadge = `<span style="font-size:10px; color:#64d2ff; background:rgba(10,132,255,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">🤖 Sugerencia IA${suggPct}</span>`;
            } else {
                confBadge = `<span style="font-size:10px; color:#8e8e93; background:rgba(255,255,255,0.06); padding:2px 7px; border-radius:8px;">Pendiente</span>`;
            }

            const avatarImgTag = (avatarUrl && avatarUrl.length > 20)
                ? `<img src="${avatarUrl}" class="person-avatar" id="pavatar-${faceNum}" alt="Face"
                        onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'44\\' height=\\'44\\' viewBox=\\'0 0 24 24\\' fill=\\'%238e8e93\\'><path d=\\'M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z\\'/></svg>';"
                        style="width:44px; height:44px; border-radius:50%; object-fit:cover;
                               border:2px solid ${hasAiSugg ? '#64d2ff' : isAlbumOwner ? '#30d158' : 'rgba(255,255,255,0.2)'};
                               box-shadow:0 2px 8px rgba(0,0,0,0.4); background:#1c1c1e;">`
                : `<div class="person-avatar" id="pavatar-${faceNum}"
                        style="width:44px; height:44px; border-radius:50%; display:flex; align-items:center; justify-content:center;
                               background:#1c1c1e; border:2px solid ${hasAiSugg ? '#64d2ff' : isAlbumOwner ? '#30d158' : 'rgba(255,255,255,0.2)'};
                               box-shadow:0 2px 8px rgba(0,0,0,0.4); font-size:20px; color:#8e8e93;">👤</div>`;

            if (mediaEl && mediaEl.tagName === 'IMG' && !mediaEl.complete) {
                mediaEl.addEventListener('load', () => {
                    const newUrl = updateAvatarCrop(mediaEl, face);
                    if (newUrl) {
                        const pavatar = document.getElementById(`pavatar-${faceNum}`);
                        if (pavatar) {
                            if (pavatar.tagName === 'IMG') {
                                pavatar.src = newUrl;
                            } else {
                                pavatar.outerHTML = `<img src="${newUrl}" class="person-avatar" id="pavatar-${faceNum}" alt="Face" style="width:44px; height:44px; border-radius:50%; object-fit:cover; border:2px solid ${hasAiSugg ? '#64d2ff' : isAlbumOwner ? '#30d158' : 'rgba(255,255,255,0.2)'}; box-shadow:0 2px 8px rgba(0,0,0,0.4); background:#1c1c1e;">`;
                            }
                        }
                    }
                }, { once: true });
            }

            card.innerHTML = `

                <div class="person-header" onclick="highlightFace(${faceNum})">

                    <div style="position:relative; flex-shrink:0;">

                        ${avatarImgTag}

                        <div style="position:absolute; bottom:-2px; right:-2px; width:16px; height:16px;

                                    background:${hasAiSugg ? '#0a84ff' : isAlbumOwner ? '#30d158' : '#3a3a3c'};

                                    border-radius:50%; border:2px solid rgba(12,13,18,0.98);

                                    font-size:8px; display:flex; align-items:center; justify-content:center; color:#fff;">

                            ${faceNum}

                        </div>

                    </div>

                    <div class="person-info" style="flex:1; min-width:0;">

                        <div style="font-size:13px; font-weight:600; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:4px;"

                             id="pname-${faceNum}">${displayTitle}</div>

                        <div id="pconf-${faceNum}">${confBadge}</div>

                    </div>

                    <button onclick="openEvolutionModal('${face.identity}'); event.stopPropagation();"

                            title="Ver evolución temporal"

                            style="flex-shrink:0; width:28px; height:28px; border-radius:8px; border:none;

                                   background:rgba(10,132,255,0.1); color:#64d2ff; cursor:pointer;

                                   font-size:13px; display:flex; align-items:center; justify-content:center;

                                   transition:all 0.15s;"

                            onmouseover="this.style.background='rgba(10,132,255,0.25)'"

                            onmouseout="this.style.background='rgba(10,132,255,0.1)'">📈</button>

                </div>

                <div id="pcard-actions-${faceNum}">

                    ${generateReassignHTML(face, faceNum, 'quickReassignFace', 'sidebar')}

                </div>

            `;

            cardsContainer.appendChild(card);
        }

        function updateAvatarCrop(mediaEl, face) {
            try {
                if (!face || face.width < 10 || face.height < 10) return '';

                const canvas = document.createElement('canvas');

                canvas.width = 120;

                canvas.height = 120;

                const ctx = canvas.getContext('2d');

                ctx.drawImage(mediaEl, Math.max(0, face.x), Math.max(0, face.y), face.width, face.height, 0, 0, 120, 120);

                return canvas.toDataURL();
            } catch(e) {
                return '';
            }
        }

        function makeBoxInteractive(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl) {
        let isDragging = false;
        let isResizing = false;
        let currentHandle = null;
        let startX, startY, startLeft, startTop, startW, startH;
        let startFace = { x: face.x, y: face.y, width: face.width, height: face.height };
        let lastActionTime = 0;
        const container = document.getElementById('lb-media-container');

        // Dragging Box
        function startDrag(e) {
            if (e.target.classList.contains('resize-handle')) return;
            if (e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION' || e.target.tagName === 'BUTTON') return;
            if (e.cancelable) e.preventDefault();
            e.stopPropagation();
            if (e.pointerId !== undefined && typeof box.setPointerCapture === 'function') { try { box.setPointerCapture(e.pointerId); } catch(err){} }

            if (Date.now() - lastActionTime < 60) return;
            lastActionTime = Date.now();

            e.stopPropagation();
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startFace = { x: face.x, y: face.y, width: face.width, height: face.height };

            const popup = box.querySelector('.lb-box-popup');
            if (popup) popup.style.display = 'none';
            const rect = box.getBoundingClientRect();
            if (popup) popup.style.display = 'flex';

            const containerRect = container.getBoundingClientRect();
            let containerW = containerRect.width;
            let containerH = containerRect.height;
            let containerLeft = containerRect.left;
            let containerTop = containerRect.top;

            if (containerW < 50) {
                const mediaRect = mediaEl.getBoundingClientRect();
                containerW = mediaRect.width;
                containerH = mediaRect.height;
                containerLeft = mediaRect.left;
                containerTop = mediaRect.top;
            }

            startLeft = rect.left - containerLeft;
            startTop = rect.top - containerTop;

            let isDragTicking = false;
            const onMove = (ev) => {
                if (!isDragging) return;
                const dx = ev.clientX - startX;
                const dy = ev.clientY - startY;

                if (Math.abs(dx) > 3 || Math.abs(dy) > 3) box.dataset.wasDragged = 'true';

                const newLeft = startLeft + dx;
                const newTop = startTop + dy;

                if (!isDragTicking) {
                    window.requestAnimationFrame(() => {
                        box.style.left = `${(newLeft / containerW) * 100}%`;
                        box.style.top = `${(newTop / containerH) * 100}%`;
                        isDragTicking = false;
                    });
                    isDragTicking = true;
                }
            };

            const onEnd = () => {
                if (isDragging) {
                    isDragging = false;
                    document.removeEventListener('pointermove', onMove);
                    document.removeEventListener('pointerup', onEnd);
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onEnd);
                    saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, startFace);
                }
            };

            document.addEventListener('pointermove', onMove);
            document.addEventListener('pointerup', onEnd);
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onEnd);
        }

        box.addEventListener('pointerdown', startDrag);
        box.addEventListener('mousedown', startDrag);

        // Resizing Box from any of the 8 handles
        function startResize(e, corner) {
            e.stopPropagation();
            if (e.cancelable) e.preventDefault();
            if (e.pointerId !== undefined && typeof e.target.setPointerCapture === 'function') { try { e.target.setPointerCapture(e.pointerId); } catch(err){} }

            if (Date.now() - lastActionTime < 60) return;
            lastActionTime = Date.now();

            isResizing = true;
            currentHandle = corner;
            startX = e.clientX;
            startY = e.clientY;
            startFace = { x: face.x, y: face.y, width: face.width, height: face.height };

            const popup = box.querySelector('.lb-box-popup');
            if (popup) popup.style.display = 'none';
            const rect = box.getBoundingClientRect();
            if (popup) popup.style.display = 'flex';

            const containerRect = container.getBoundingClientRect();
            let containerW = containerRect.width;
            let containerH = containerRect.height;
            let containerLeft = containerRect.left;
            let containerTop = containerRect.top;

            if (containerW < 50) {
                const mediaRect = mediaEl.getBoundingClientRect();
                containerW = mediaRect.width;
                containerH = mediaRect.height;
                containerLeft = mediaRect.left;
                containerTop = mediaRect.top;
            }

            startLeft = rect.left - containerLeft;
            startTop = rect.top - containerTop;
            startW = rect.width;
            startH = rect.height;

            let isResizeTicking = false;
            const onResizeMove = (ev) => {
                if (!isResizing) return;
                box.dataset.wasDragged = 'true';

                const dx = ev.clientX - startX;
                const dy = ev.clientY - startY;
                let newW = startW;
                let newH = startH;
                let newLeft = startLeft;
                let newTop = startTop;

                if (currentHandle.includes('r')) {
                    newW = Math.max(25, startW + dx);
                } else if (currentHandle.includes('l')) {
                    newW = Math.max(25, startW - dx);
                    if (newW > 25) newLeft = startLeft + dx;
                }

                if (currentHandle.includes('b')) {
                    newH = Math.max(25, startH + dy);
                } else if (currentHandle.includes('t')) {
                    newH = Math.max(25, startH - dy);
                    if (newH > 25) newTop = startTop + dy;
                }

                if (!isResizeTicking) {
                    window.requestAnimationFrame(() => {
                        box.style.width = `${(newW / containerW) * 100}%`;
                        box.style.height = `${(newH / containerH) * 100}%`;
                        box.style.left = `${(newLeft / containerW) * 100}%`;
                        box.style.top = `${(newTop / containerH) * 100}%`;
                        isResizeTicking = false;
                    });
                    isResizeTicking = true;
                }
            };

            const onResizeEnd = () => {
                if (isResizing) {
                    isResizing = false;
                    document.removeEventListener('pointermove', onResizeMove);
                    document.removeEventListener('pointerup', onResizeEnd);
                    document.removeEventListener('mousemove', onResizeMove);
                    document.removeEventListener('mouseup', onResizeEnd);
                    saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, startFace);
                }
            };

            document.addEventListener('pointermove', onResizeMove);
            document.addEventListener('pointerup', onResizeEnd);
            document.addEventListener('mousemove', onResizeMove);
            document.addEventListener('mouseup', onResizeEnd);
        }

        const handles = box.querySelectorAll('.resize-handle');
        handles.forEach(handle => {
            const corner = handle.dataset.corner;
            handle.addEventListener('pointerdown', (e) => startResize(e, corner));
            handle.addEventListener('mousedown', (e) => startResize(e, corner));
        });
    }

    function saveBoxDimensions(box, face, faceNum, intrinsicWidth, intrinsicHeight, mediaEl, oldFace) {
        const leftPct = parseFloat(box.style.left) / 100;
        const topPct = parseFloat(box.style.top) / 100;
        const widthPct = parseFloat(box.style.width) / 100;
        const heightPct = parseFloat(box.style.height) / 100;

        if (isNaN(leftPct) || isNaN(topPct) || isNaN(widthPct) || isNaN(heightPct) || widthPct <= 0 || heightPct <= 0) {
            return;
        }

        face.x = Math.max(0, Math.round(leftPct * intrinsicWidth));
        face.y = Math.max(0, Math.round(topPct * intrinsicHeight));
        face.width = Math.min(intrinsicWidth - face.x, Math.round(widthPct * intrinsicWidth));
        face.height = Math.min(intrinsicHeight - face.y, Math.round(heightPct * intrinsicHeight));

        if (face.width < 20 || face.height < 20) {
            return;
        }

        // Update dataset coordinates on the element
        box.dataset.faceX = face.x;
        box.dataset.faceY = face.y;
        box.dataset.faceW = face.width;
        box.dataset.faceH = face.height;

        // Clean any duplicate box elements with same id in DOM
        const duplicateBoxes = document.querySelectorAll(`.lb-bounding-box#bbox-${faceNum}`);
        if (duplicateBoxes.length > 1) {
            duplicateBoxes.forEach(b => {
                if (b !== box) b.remove();
            });
        }

        // Update avatar in sidebar
        const avatarImg = document.getElementById(`pavatar-${faceNum}`);
        if (avatarImg) {
            avatarImg.src = updateAvatarCrop(mediaEl, face);
        }

        // Guardar permanentemente en backend y activar Reaprendizaje Activo
        if (face.identity && face.identity !== "Desconocido") {
            let pathParts3 = currentFileObj.path.split(/[\\/]/);
            let folderName = pathParts3.slice(-2, -1)[0];
            let categoryName = pathParts3.slice(-3, -2)[0];
            if (folderName === '_Dudosos') {
                folderName = pathParts3.slice(-3, -2)[0];
                categoryName = pathParts3.slice(-4, -3)[0];
            }

            fetch('/api/correct', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    path: currentFileObj.path,
                    new_categoria: categoryName,
                    new_identidad: face.identity,
                    face: {x: face.x, y: face.y, width: face.width, height: face.height},
                    old_face: oldFace || null,
                    face_num: faceNum || 1,
                    apply_to_duplicates: true
                })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showToast('Recuadro guardado correctamente.');
                    if (data.new_path) {
                        if (currentFileObj) currentFileObj.path = data.new_path.replace(/\\/g, '/');
                    }
                } else if (data.error) {
                    alert("Error: " + data.error);
                }
            }).catch(err => {
                console.error("Error guardando dimensiones de recuadro:", err);
            });
        }
    }

    async function ignoreUnconfirmedFaces() {
            if (!currentFaces || currentFaces.length === 0) return;

            // Collect unconfirmed faces

            const unconfirmed = [];

            currentFaces.forEach((face, idx) => {
                if (face.identity === 'Desconocido' || face.identity.startsWith('IA (Pendiente)')) {
                    unconfirmed.push({ face: face, faceNum: idx + 1 });
                }
            });

            if (unconfirmed.length === 0) {
                showToast("No hay caras sin confirmar.");

                return;
            }

            if (!confirm(`¿Ignorar ${unconfirmed.length} caras no confirmadas?`)) return;

            document.getElementById('btn-ignore-unconfirmed').textContent = "Ignorando...";

            document.getElementById('btn-ignore-unconfirmed').style.opacity = '0.5';

            document.getElementById('btn-ignore-unconfirmed').style.pointerEvents = 'none';

            for (let i = 0; i < unconfirmed.length; i++) {
                const item = unconfirmed[i];
                const face = item.face;
                let idObj = {categoria: "Ignorar", identidad: "Ignorar_Irrelevante"};

                try {
                    const res = await fetch('/api/correct', {
                        method: 'POST',

                        headers: {'Content-Type': 'application/json'},

                        body: JSON.stringify({
                            path: currentFileObj.path,

                            new_categoria: idObj.categoria,

                            new_identidad: idObj.identidad,

                            face: {
                            x: face.box ? face.box[0] : (face.x || 0),

                            y: face.box ? face.box[1] : (face.y || 0),

                            width: face.box ? face.box[2] : (face.width || 0),

                            height: face.box ? face.box[3] : (face.height || 0)
                        },

                            apply_to_duplicates: false
                        })
                    });

                    const data = await res.json();

                    if(data.success && data.new_path && currentFileObj) {
                        currentFileObj.path = data.new_path;
                    }
                } catch(e) {
                    console.error("Error ignoring face", e);
                }
            }

            showToast(`${unconfirmed.length} caras ignoradas.`);

            // Refresh

            if (currentCat === 'Limpieza Inteligente') {
                const gridItem = document.getElementById('grid-container').children[currentItemIndex];

                if (gridItem) {
                    gridItem.style.opacity = '0.3';

                    gridItem.style.pointerEvents = 'none';
                }
            } else if (currentCat && currentIdent) {
                renderGrid(currentCat, currentIdent);
            }

            // Re-open lightbox to refresh faces list

            openLightbox(currentFileObj);
        }

        async function quickReassignFace(valStr, faceNum) {
            const face = currentFaces[faceNum - 1];

            if (!face) return;

            await inlineCorrect(encodeURIComponent(currentFileObj.path), valStr, faceNum, face.x, face.y, face.width, face.height);
        }

        async function inlineCorrect(pathEncoded, valStr, faceNum, faceX, faceY, faceW, faceH) {
            if(!valStr) return;

            const targetPath = (currentFileObj && currentFileObj.path) ? currentFileObj.path : decodeURIComponent(pathEncoded);

            if(!targetPath) return;

            const safeX = (faceX !== undefined && faceX !== 'undefined' && faceX !== null) ? parseFloat(faceX) : 0;
            const safeY = (faceY !== undefined && faceY !== 'undefined' && faceY !== null) ? parseFloat(faceY) : 0;
            const safeW = (faceW !== undefined && faceW !== 'undefined' && faceW !== null) ? parseFloat(faceW) : 100;
            const safeH = (faceH !== undefined && faceH !== 'undefined' && faceH !== null) ? parseFloat(faceH) : 100;
            let idObj;

            if(valStr === 'NEW') {
                const newCat = prompt("Introduce la categoría:", "Conocidos");

                if(!newCat) return;

                const newIdent = prompt("Introduce el nombre completo:");

                if(!newIdent) return;

                idObj = {categoria: newCat, identidad: newIdent};
            } else {
                idObj = JSON.parse(valStr);
            }

            // Confirmación explícita para prevenir cambios accidentales al tocar la pantalla

            const personName = idObj.identidad || 'esta persona';
            let confirmMsg = `¿Confirmar esta cara como "${personName}"?`;

            if (idObj.identidad === 'YO') {
                confirmMsg = '¿Confirmar que esta cara eres TÚ (Eneko)?';
            } else if (idObj.identidad === 'Desconocido') {
                const currentFaceIdent = (faceNum && currentFaces && currentFaces[faceNum - 1] && currentFaces[faceNum - 1].identity) ? currentFaces[faceNum - 1].identity.replace(/^IA\s*\(Pendiente\):\s*/i, '').replace(/^\?\s*/, '') : '';

                confirmMsg = currentFaceIdent ? `¿Confirmar que esta persona NO es ${currentFaceIdent}?` : '¿Marcar esta cara como Desconocida?';
            } else if (idObj.identidad === 'Falso_Positivo' || idObj.identidad === 'Ignorar_Irrelevante') {
                confirmMsg = '¿Descartar esta cara como irrelevante o falso positivo?';
            }

            if (!confirm(confirmMsg)) {
                return;
            }

            // Llamada directa y ultra-rápida (no bloqueante para la UI)

            const res = await fetch('/api/correct', {
                method: 'POST',

                headers: {'Content-Type': 'application/json'},

                body: JSON.stringify({
                    path: targetPath,

                    new_categoria: idObj.categoria,

                    new_identidad: idObj.identidad,

                    face: {x: safeX, y: safeY, width: safeW, height: safeH},

                    apply_to_duplicates: false
                })
            });

            const data = await res.json();

            if(data.success) {
                // GUARD ESTRICTO: Si el usuario ya cambió de foto en el visor mientras la petición estaba en curso,

                // NO mutar las caras ni el DOM de la nueva foto abierta actualmente.

                if (!currentFileObj || currentFileObj.path !== targetPath) {
                    if (typeof showToast === 'function') {
                        showToast(`Asignado a ${targetIdentity}`);
                    }
                    return;
                }

                if (data.new_path && currentFileObj) {
                    currentFileObj.path = data.new_path;

                    document.querySelectorAll('.lb-bounding-box').forEach(b => {
                        b.dataset.path = data.new_path;
                    });
                }

                if (idObj.identidad === 'Falso_Positivo' || idObj.identidad === 'Ignorar_Irrelevante') {
                    // Guardar cara descartada para permitir Deshacer inmediato

                    window.lastDiscardedFace = {
                        path: targetPath,

                        face: {x: safeX, y: safeY, width: safeW, height: safeH, identity: idObj.identidad}
                    };

                    const bbox = document.getElementById(`bbox-${faceNum}`);
                    const pcard = document.getElementById(`pcard-${faceNum}`);

                    if (bbox) bbox.remove();

                    if (pcard) pcard.remove();

                    showToast(`Cara descartada. <button onclick="undoLastDiscard()" style="background:#ff9f0a; color:#000; border:none; border-radius:4px; padding:3px 8px; margin-left:8px; font-weight:700; cursor:pointer;">↩ Deshacer</button>`);

                    return;
                }

                // 1. Actualizar estado local en memoria

                if (currentFaces && currentFaces[faceNum - 1]) {
                    currentFaces[faceNum - 1].identity = idObj.identidad;

                    currentFaces[faceNum - 1].confidence = 1.0;

                    currentFaces[faceNum - 1].is_manual = true;

                    currentFaces[faceNum - 1].suggested_identity = null;
                }

                showToast(`Asignado a '${cleanDisplayName(idObj.identidad)}'. La IA ha aprendido esta asignación.`);

                // 2. Actualizar visualmente la tarjeta de la persona sin parpadeos ni recargas bloqueantes

                const pname = document.getElementById(`pname-${faceNum}`);
                const pconf = document.getElementById(`pconf-${faceNum}`);
                const pcardActions = document.getElementById(`pcard-actions-${faceNum}`);

                if (pname) pname.textContent = `#${faceNum} ${cleanDisplayName(idObj.identidad)}`;

                if (pconf) pconf.innerHTML = `<span style="font-size:10px; color:#ff9f0a; background:rgba(255,159,10,0.12); padding:2px 7px; border-radius:8px; font-weight:600;">✏️ Editado (Manual)</span>`;

                if (pcardActions && currentFaces && currentFaces[faceNum - 1]) {
                    pcardActions.innerHTML = generateReassignHTML(currentFaces[faceNum - 1], faceNum, 'quickReassignFace', 'sidebar');
                }

                // Mutual exclusion: Re-render ALL other face action cards in this photo immediately

                if (currentFaces && Array.isArray(currentFaces)) {
                    currentFaces.forEach((f, idx) => {
                        const fn = idx + 1;

                        if (fn !== faceNum) {
                            if (f.suggested_identity === idObj.identidad) {
                                f.suggested_identity = null;
                            }

                            const otherActions = document.getElementById(`pcard-actions-${fn}`);

                            if (otherActions) {
                                otherActions.innerHTML = generateReassignHTML(f, fn, 'quickReassignFace', 'sidebar');
                            }
                        }
                    });
                }

                if (currentFileObj) {
                    if (currentFileObj.source && !currentFileObj.source.includes("Manual")) {
                        currentFileObj.source = currentFileObj.source + " + Manual";
                    }

                    const gridBadge = document.getElementById(`source-${currentItemIndex}`);

                    if (gridBadge) {
                        if (currentFileObj.source && currentFileObj.source.includes('Dataset')) {
                            gridBadge.className = 'badge badge-dataset';

                            gridBadge.textContent = '🔒 Dataset + ✏️ Manual';
                        } else {
                            gridBadge.className = 'badge badge-manual';

                            gridBadge.textContent = '✏️ Manual';
                        }
                    }
                }

                const isFromDudosos = currentCat === '_Dudosos' || currentIdent === '_Dudosos' || (currentFileObj && currentFileObj.path && currentFileObj.path.includes('_Dudosos')) || (currentCat && currentCat.includes('Revisar')) || (currentIdent && currentIdent.includes('Revisar'));
                const isReassignedAway = Boolean(currentIdent && idObj.identidad && idObj.identidad !== currentIdent && !isFromDudosos);
                const personStillInPhoto = Boolean(currentFaces && currentFaces.some(f => f.identity === currentIdent));

                if ((isFromDudosos && idObj.identidad !== 'Desconocido') || (isReassignedAway && !personStillInPhoto)) {
                    // Actualizar silenciosamente la tarjeta en la cuadrícula de fondo SIN expulsar al usuario del visor

                    const gridContainer = document.getElementById('grid-container');

                    if (gridContainer && gridContainer.children[currentItemIndex]) {
                        const card = gridContainer.children[currentItemIndex];

                        card.style.transition = 'opacity 0.3s ease';

                        card.style.opacity = '0.5';
                    }

                    // MANTENER AL USUARIO EN LA MISMA IMAGEN: Puede seguir confirmando o reasignando caras

                    console.log("[LIGHTBOX] Foto reasignada con éxito, manteniendo visor abierto en la imagen actual.");
                }
            } else {
                showToast(data.error || "Error al asignar.", true);
            }
        }

        window.undoLastDiscard = async function() {
            if (!window.lastDiscardedFace) return;

            const { path, face } = window.lastDiscardedFace;

            window.lastDiscardedFace = null;

            showToast("Restaurando cara...");

            try {
                const res = await fetch('/api/undo_discard', {
                    method: 'POST',

                    headers: {'Content-Type': 'application/json'},

                    body: JSON.stringify({ path, face })
                });

                const data = await res.json();

                if (data.success) {
                    showToast("✅ Cara restaurada correctamente.");

                    runAnalysis();
                } else {
                    showToast("Error al restaurar: " + (data.error || ''), true);
                }
            } catch (err) {
                showToast("Error de conexión al restaurar cara.", true);
            }
        };

        window.enableManualSelection = enableManualSelection;

        function enableManualSelection() {
            if (!currentFileObj) return;

            if (typeof resetZoom === 'function') resetZoom();

            window.isDrawingMode = true;

            const container = document.getElementById('lb-media-container');
            const mediaEl = container ? container.querySelector('.lb-media-element') : null;

            if (!mediaEl) return;

            mediaEl.draggable = false;

            showToast("Arrastra sobre la foto para crear un recuadro de persona (funciona con Zoom).");

            container.style.cursor = 'crosshair';

            let startPctX, startPctY, selectBox, isDrawing = false;
            const onMouseDown = (e) => {
                e.preventDefault();

                e.stopPropagation();

                isDrawing = true;

                const rect = mediaEl.getBoundingClientRect();

                startPctX = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));

                startPctY = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

                selectBox = document.createElement('div');

                selectBox.style.cssText = `position:absolute; left:${startPctX * 100}%; top:${startPctY * 100}%; border:2px dashed #30d158; background:rgba(48,209,88,0.25); pointer-events:none; z-index:9999; box-sizing:border-box;`;

                container.appendChild(selectBox);

                const onMouseMove = (ev) => {
                    if (!isDrawing) return;

                    const curRect = mediaEl.getBoundingClientRect();
                    const curPctX = Math.max(0, Math.min(1, (ev.clientX - curRect.left) / curRect.width));
                    const curPctY = Math.max(0, Math.min(1, (ev.clientY - curRect.top) / curRect.height));
                    const minPctX = Math.min(startPctX, curPctX);
                    const minPctY = Math.min(startPctY, curPctY);
                    const wPct = Math.abs(curPctX - startPctX);
                    const hPct = Math.abs(curPctY - startPctY);

                    selectBox.style.left = `${minPctX * 100}%`;

                    selectBox.style.top = `${minPctY * 100}%`;

                    selectBox.style.width = `${wPct * 100}%`;

                    selectBox.style.height = `${hPct * 100}%`;
                };

                const onMouseUp = async (ev) => {
                    if (!isDrawing) return;

                    isDrawing = false;

                    document.removeEventListener('mousemove', onMouseMove);

                    document.removeEventListener('mouseup', onMouseUp);

                    container.removeEventListener('mousedown', onMouseDown);

                    container.style.cursor = 'default';

                    window.isDrawingMode = false;

                    const curRect = mediaEl.getBoundingClientRect();
                    const endPctX = Math.max(0, Math.min(1, (ev.clientX - curRect.left) / curRect.width));
                    const endPctY = Math.max(0, Math.min(1, (ev.clientY - curRect.top) / curRect.height));
                    const leftPct = Math.min(startPctX, endPctX);
                    const topPct = Math.min(startPctY, endPctY);
                    const widthPct = Math.abs(endPctX - startPctX);
                    const heightPct = Math.abs(endPctY - startPctY);

                    if (selectBox) selectBox.remove();

                    if (widthPct < 0.01 || heightPct < 0.01) return;

                    let isCurrentVideo = mediaEl.tagName === 'VIDEO';
                    let intrinsicWidth = (isCurrentVideo ? mediaEl.videoWidth : mediaEl.naturalWidth) || mediaEl.clientWidth || mediaEl.offsetWidth || 800;
                    let intrinsicHeight = (isCurrentVideo ? mediaEl.videoHeight : mediaEl.naturalHeight) || mediaEl.clientHeight || mediaEl.offsetHeight || 600;
                    let realX = Math.round(leftPct * intrinsicWidth);
                    let realY = Math.round(topPct * intrinsicHeight);
                    let realW = Math.round(widthPct * intrinsicWidth);
                    let realH = Math.round(heightPct * intrinsicHeight);

                    realX = Math.max(0, realX);

                    realY = Math.max(0, realY);

                    if (realX + realW > intrinsicWidth) realW = intrinsicWidth - realX;

                    if (realY + realH > intrinsicHeight) realH = intrinsicHeight - realY;

                    const newFace = { x: realX, y: realY, width: realW, height: realH, identity: "Desconocido", confidence: "Selección manual" };
                    const nextNum = document.querySelectorAll('.lb-bounding-box').length + 1;
                    const cardsContainer = document.getElementById('person-cards-container');

                    createFaceElements(newFace, nextNum, intrinsicWidth, intrinsicHeight, mediaEl, container, cardsContainer);

                    highlightFace(nextNum);

                    const select = document.getElementById(`pselect-${nextNum}`);

                    if (select) {
                        select.focus();

                        select.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }

                    showToast(`Recuadro #${nextNum} listo. Selecciona la persona en el panel lateral.`);
                };

                document.addEventListener('mousemove', onMouseMove);

                document.addEventListener('mouseup', onMouseUp);
            };

            container.addEventListener('mousedown', onMouseDown);
        }

        window.enableManualSelection = enableManualSelection;

