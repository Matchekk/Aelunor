/**
 * One-shot build: headless Motion Canvas render, then packaging into runtime
 * WebP assets. If no Chromium-family browser is available, falls back to
 * slicing the source sprite sheet with sharp so the build still succeeds.
 */
import {spawnSync} from 'node:child_process';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

function run(script, args = []) {
  const result = spawnSync(process.execPath, [join(root, 'scripts', script), ...args], {
    cwd: root,
    stdio: 'inherit',
  });
  return result.status === 0;
}

if (run('render-headless.mjs')) {
  if (!run('package-assets.mjs')) {
    process.exit(1);
  }
} else {
  console.warn('[build] headless render failed; falling back to direct sprite-sheet slicing');
  if (!run('package-assets.mjs', ['--from-spritesheet'])) {
    process.exit(1);
  }
}
