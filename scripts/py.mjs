#!/usr/bin/env node
/**
 * Cross-platform runner for backend commands.
 *
 * Resolves the backend virtualenv interpreter (platform-aware) and forwards
 * arguments to it with the backend/ directory as CWD, so `app` is importable.
 *
 * Usage: node scripts/py.mjs -m pytest -q
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const backendDir = path.join(repoRoot, 'backend');

const venvPython =
  process.platform === 'win32'
    ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
    : path.join(backendDir, '.venv', 'bin', 'python');

const fallback = process.platform === 'win32' ? 'python' : 'python3';
const interpreter = fs.existsSync(venvPython) ? venvPython : fallback;

if (interpreter === fallback) {
  console.warn(`[py] venv interpreter not found, falling back to "${fallback}".`);
}

const result = spawnSync(interpreter, process.argv.slice(2), {
  cwd: backendDir,
  stdio: 'inherit',
});

process.exit(result.status ?? 1);
