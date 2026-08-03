// @ts-nocheck
import { store } from './store';
import { renderGrid } from './ui/grid';

export async function loadIdentities() {
    const res = await fetch('/api/identities');
    store.identitiesList = await res.json();
    window.identitiesList = store.identitiesList;
}

export async function loadGallery() {
    const res = await fetch('/api/gallery');
    store.fullGallery = await res.json();
    window.fullGallery = store.fullGallery;
    if (window.renderTree) window.renderTree();
    if (store.currentCat && store.currentIdent) {
        renderGrid(store.currentCat, store.currentIdent);
    }
}
window.loadIdentities = loadIdentities;
window.loadGallery = loadGallery;
