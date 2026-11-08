/**
 * Sidebar & Drill-Down Albums Navigation Module
 * Implements Apple iOS NavigationController-style drill-down for albums:
 * Level 1: Clean category cards (YO, Familia, Conocidos, etc.) with badges and chevrons.
 * Level 2: Dedicated category view with instant search filter, lazy avatars, and back navigation.
 */

export const CAT_ICONS = {
    'YO': '👤',
    'Conocidos': '👥',
    'Familia': '👨‍👩‍👧',
    'Lugares': '📍',
    'Eventos': '🎉',
    'Mascotas': '🐶',
    'Objetos': '🚗',
    'Profesores': '🎓',
    'Recuerdos': '📸',
    'Publicaciones_Instagram': '📱',
    '📋 Revisión / Por Organizar': '📋'
};

export const CAT_ORDER = [
    'YO', 
    '📋 Revisión / Por Organizar', 
    'Familia', 
    'Conocidos', 
    'Lugares', 
    'Eventos', 
    'Mascotas', 
    'Objetos', 
    'Recuerdos', 
    'Profesores', 
    'Publicaciones_Instagram'
];
