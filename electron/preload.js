/**
 * Preload script — the only bridge between the renderer and the main process.
 * Business logic never crosses this boundary; only safe, explicit handles.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('longvid', {
  /** Base URL of the local backend, e.g. http://127.0.0.1:8790 */
  getBackendBaseUrl: () => ipcRenderer.invoke('longvid:get-backend-url'),
  platform: process.platform,
});
