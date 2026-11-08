/**
 * Header & Navigation Module
 * Controls 3-dots overflow popover menu, grid density, and header collapse state.
 */

export function initHeaderControls() {
    window.toggleHeaderOptionsMenu = function(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        const menu = document.getElementById('header-options-dropdown');
        if (!menu) return;
        const isHidden = window.getComputedStyle(menu).display === 'none';
        menu.style.display = isHidden ? 'block' : 'none';
    };

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        const menu = document.getElementById('header-options-dropdown');
        const btn = document.getElementById('btn-header-more');
        if (menu && menu.style.display === 'block') {
            if (!menu.contains(e.target) && !btn?.contains(e.target)) {
                menu.style.display = 'none';
            }
        }
    });

    // Close menu on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const menu = document.getElementById('header-options-dropdown');
            if (menu && menu.style.display === 'block') {
                menu.style.display = 'none';
            }
        }
    });
}
