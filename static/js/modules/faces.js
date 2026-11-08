/**
 * Faces & Identity Module
 * Manages face bounding box rendering, mutual exclusion per photo,
 * and keep-in-place reassignment.
 */

export function extractClaimedIdentities(item) {
    const claimed = new Set();
    if (!item || !item.faces) return claimed;
    
    item.faces.forEach(face => {
        const id = face.identity || face.person_name || face.name;
        if (id && !id.toLowerCase().includes('desconocid') && !id.startsWith('?') && !id.includes('Persona Nueva')) {
            claimed.add(id);
        }
    });
    return claimed;
}

export function filterMutualExclusionSuggestions(suggestions, claimedIdentities) {
    if (!Array.isArray(suggestions)) return [];
    return suggestions.filter(s => {
        const name = typeof s === 'string' ? s : s.name;
        return !claimedIdentities.has(name);
    });
}
