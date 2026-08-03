// @ts-nocheck
export const store = {
    fullGallery: {},
    identitiesList: [],
    currentCat: null,
    currentIdent: null,
    currentFolderItems: [],
    currentItemIndex: -1,
    isSwipeModeActive: true,
    isMultiSelectMode: false,
    selectedFiles: new Set()
};
window.store = store;
