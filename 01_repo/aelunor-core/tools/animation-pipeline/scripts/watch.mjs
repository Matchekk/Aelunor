/**
 * Fast iteration loop for scene authoring: keeps the Vite dev server and the
 * headless browser alive and re-renders whenever a file under src/ changes,
 * then repackages. Render cycles drop from ~10s (cold start) to ~2s.
 *
 *   node scripts/watch.mjs [--project logoProject] [--vars <json>]
 *       [--name <output-name>] [--once]
 *
 * Packaging uses package-animation.mjs with dedup + crop; --name defaults to
 * "<project>-watch". --once runs a single cycle and exits (for testing).
 */
import {spawnSync} from 'node:child_process';
import {mkdirSync, readdirSync, rmSync, statSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import {chromium} from 'playwright-core';
import {createServer} from 'vite';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

function getArg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}
const PROJECT = getArg('project', 'logoProject');
const VARS = getArg('vars', null);
const NAME = getArg('name', `${PROJECT}-watch`);
const ONCE = process.argv.includes('--once');
const outputDir = join(root, 'output', PROJECT);

function srcSnapshot() {
  const entries = readdirSync(join(root, 'src'), {recursive: true}).map(String);
  return entries
    .map(entry => {
      const path = join(root, 'src', entry);
      try {
        return `${entry}:${statSync(path).mtimeMs}`;
      } catch {
        return entry;
      }
    })
    .join('|');
}

async function launchBrowser() {
  for (const channel of ['msedge', 'chrome']) {
    try {
      return await chromium.launch({channel, headless: true});
    } catch {
      // try next channel
    }
  }
  throw new Error('No Edge/Chrome found for headless rendering.');
}

const server = await createServer({
  root,
  logLevel: 'warn',
  server: {port: 9426, strictPort: false, open: false},
});
await server.listen();
const url = server.resolvedUrls.local[0];
const browser = await launchBrowser();
const page = await browser.newPage();
page.on('pageerror', error => console.error(`[browser] ${error.message}`));

async function cycle() {
  const started = Date.now();
  rmSync(outputDir, {recursive: true, force: true});
  mkdirSync(outputDir, {recursive: true});

  const varsQuery = VARS ? `&vars=${encodeURIComponent(VARS)}` : '';
  await page.goto(`${url}render.html?project=${PROJECT}${varsQuery}&t=${started}`, {
    waitUntil: 'domcontentloaded',
  });
  await page.waitForFunction(
    () => window.__renderDone === true || typeof window.__renderError === 'string',
    undefined,
    {timeout: 120_000},
  );
  const renderError = await page.evaluate(() => window.__renderError);
  if (renderError) {
    console.error(`[watch] render failed:\n${renderError}`);
    return;
  }

  const result = spawnSync(
    process.execPath,
    [
      join(root, 'scripts/package-animation.mjs'),
      '--frames', join('output', PROJECT),
      '--name', NAME,
      '--fuzz', '0.4',
      // Preview encode: speed over size; final assets go through npm run
      // animate / logo with full effort.
      '--effort', '0',
      '--quality', '80',
    ],
    {cwd: root, stdio: 'inherit'},
  );
  if (result.status === 0) {
    console.log(`[watch] cycle done in ${((Date.now() - started) / 1000).toFixed(1)}s`);
  }
}

console.log(`[watch] project=${PROJECT} -> output/${NAME}.webp (Ctrl+C to stop)`);
await cycle();
if (ONCE) {
  await browser.close();
  await server.close();
  process.exit(0);
}

let snapshot = srcSnapshot();
setInterval(async () => {
  const current = srcSnapshot();
  if (current !== snapshot) {
    snapshot = current;
    console.log('[watch] change detected, re-rendering...');
    await cycle();
    snapshot = srcSnapshot();
  }
}, 1000);
