/**
 * Electron main process — thin desktop shell only.
 *
 * Responsibilities (per docs/architecture.md and AGENTS.md):
 *  - create the application window,
 *  - spawn the FastAPI backend and wait for it to become healthy,
 *  - expose a minimal, safe IPC bridge via the preload script,
 *  - shut the backend down cleanly.
 *
 * No business logic lives here.
 */

const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { spawn } = require('node:child_process');
const path = require('node:path');
const process = require('node:process');

const REPO_ROOT = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(REPO_ROOT, 'backend');
const BACKEND_PORT = Number(process.env.LONGVID_PORT || 8790);
const API_BASE = `http://127.0.0.1:${BACKEND_PORT}`;
const VITE_ORIGIN = 'http://127.0.0.1:5173';
const HEALTH_URL = `${API_BASE}/api/health`;
const STARTUP_TIMEOUT_MS = 60000;
const POLL_INTERVAL_MS = 500;

let backendProcess = null;
let mainWindow = null;

/** Candidate interpreters, in preference order: project venv, then system python. */
function pythonCandidates() {
  if (process.platform === 'win32') {
    return [
      path.join(BACKEND_DIR, '.venv', 'Scripts', 'python.exe'),
      path.join(BACKEND_DIR, '.venv', 'Scripts', 'python'),
      'python',
    ];
  }
  return [path.join(BACKEND_DIR, '.venv', 'bin', 'python'), 'python3'];
}

function spawnBackend() {
  for (const interpreter of pythonCandidates()) {
    try {
      const child = spawn(interpreter, ['-m', 'app.main'], {
        cwd: BACKEND_DIR,
        env: { ...process.env, LONGVID_PORT: String(BACKEND_PORT) },
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      child.on('error', (error) => console.error('[backend] failed to launch:', error.message));
      child.stdout.on('data', (chunk) => console.log(`[backend] ${chunk}`.trimEnd()));
      child.stderr.on('data', (chunk) => console.error(`[backend] ${chunk}`.trimEnd()));
      console.log(`[backend] launched with ${interpreter}`);
      return child;
    } catch (error) {
      console.error(`[backend] could not use ${interpreter}:`, error.message);
    }
  }
  return null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return true;
    } catch {
      // not up yet
    }
    await sleep(POLL_INTERVAL_MS);
  }
  return false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: 'LongVid',
    backgroundColor: '#0f1115',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const startUrl = process.env.VITE_DEV_SERVER_URL || VITE_ORIGIN;

  if (!app.isPackaged) {
    // Dev: wait for the Vite dev server (started by the root `npm run dev`).
    waitFor(startUrl, 30000).then((ready) => {
      if (ready) mainWindow.loadURL(startUrl);
      else mainWindow.loadURL('data:text/html,<h1>LongVid</h1><p>Vite dev server did not start.</p>');
    });
  } else {
    mainWindow.loadFile(path.join(REPO_ROOT, 'frontend', 'dist', 'index.html'));
  }
}

app.whenReady().then(async () => {
  ipcMain.handle('longvid:get-backend-url', () => API_BASE);
  ipcMain.handle('longvid:choose-video', async () => {
    // Native file dialog; the backend validates and copies the file into the
    // project workspace, so no untrusted path is ever executed.
    const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
      title: 'Import video',
      properties: ['openFile'],
      filters: [{ name: 'Video', extensions: ['mp4', 'mov', 'mkv', 'webm', 'avi'] }],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  backendProcess = spawnBackend();
  const healthy = backendProcess ? await waitFor(HEALTH_URL, STARTUP_TIMEOUT_MS) : false;
  if (!healthy) {
    console.warn('[backend] did not report healthy in time; continuing anyway.');
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  app.quit();
});

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});
