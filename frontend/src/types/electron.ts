/** Ambient types for the Electron preload bridge (contextBridge surface). */

export interface LongVidBridge {
  /** Base URL of the local backend, e.g. http://127.0.0.1:8790 */
  getBackendBaseUrl(): Promise<string>;
  /** Opens the native file dialog and returns an absolute path or null. */
  chooseVideo(): Promise<string | null>;
  platform: string;
}

declare global {
  interface Window {
    longvid?: LongVidBridge;
  }
}

export {};
