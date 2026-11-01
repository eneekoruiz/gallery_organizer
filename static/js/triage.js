// ============================================================
// TRIAGE.JS - AI Suggestions & Group Reviews
// ============================================================

window.loadSidebarIASuggestions = async function() {
    const container = document.getElementById('ia-suggestions-container');
    const list = document.getElementById('ia-suggestions-list');
    if (!container || !list) return;

    try {
        const res = await fetch('/api/suggest_merges');
        if (!res.ok) {
            container.style.display = 'none';
            return;
        }

        const data = await res.json();
        const suggestions = data.suggestions || [];

        if (suggestions.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        list.innerHTML = suggestions.slice(0, 4).map(sug => {
            const pct = Math.round((sug.similarity || 0.85) * 100);
            return `
                <div class="ia-suggestion-card" style="background:rgba(255,255,255,0.04); border:1px solid rgba(191,90,242,0.25); border-radius:10px; padding:8px 10px; margin-bottom:6px; cursor:pointer; transition:all 0.18s ease;"
                     onmouseover="this.style.background='rgba(191,90,242,0.12)'; this.style.borderColor='rgba(191,90,242,0.6)';"
                     onmouseout="this.style.background='rgba(255,255,255,0.04)'; this.style.borderColor='rgba(191,90,242,0.25)';"
                     onclick='window.handleSuggestionClick(${JSON.stringify(sug)})'>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:11px; font-weight:700; color:#64d2ff;">${pct}% Similitud</span>
                        <span style="font-size:10px; color:#30d158; font-weight:600;">Fusión IA</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:6px; font-size:11px; color:#fff;">
                        <span style="color:#ff9f0a; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:85px;" title="${sug.source}">${sug.source}</span>
                        <span style="color:#8e8e93;">→</span>
                        <span style="color:#30d158; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:85px;" title="${sug.target}">${sug.target}</span>
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        container.style.display = 'none';
    }
};

window.handleSuggestionClick = function(sug) {
    if (typeof window.openSuggestionPreviewModal === 'function') {
        window.openSuggestionPreviewModal(sug);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(window.loadSidebarIASuggestions, 2000);
});
