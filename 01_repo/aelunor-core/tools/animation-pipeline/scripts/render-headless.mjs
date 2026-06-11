/**
 * Headless Motion Canvas render: starts the Vite dev server programmatically,
 * opens render.html in a headless Chromium-family browser, and waits until the
 * image-sequence exporter has written all frames to ./output.
 *
 * No browser download is required: an installed Edge or Chrome is reused via
 * playwright-core release channels.
 */
import {existsSync, mkdirSync, readdirSync, rmSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import {chromium} from 'playwright-core';
import {createServer} from 'vite';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const projectIndex = process.argv.indexOf('--project');
const projectName = projectIndex >= 0 ? process.argv[projectIndex + 1] : 'project';
// The exporter writes to output/<projectName>; only that subfolder is cleaned
// so artifacts of other projects survive.
const outputDir = join(root, 'output', projectName);
const RENDER_TIMEOUT_MS = 120_000;
const BROWSER_CHANNELS = ['msedge', 'chrome'];

async function launchBrowser() {
  const errors = [];
  for (const channel of BROWSER_CHANNELS) {
    try {
      return await chromium.launch({channel, headless: true});
    } catch (error) {
      errors.push(`${channel}: ${error.message?.split('\n')[0]}`);
    }
  }
  if (process.env.ANIMATION_PIPELINE_BROWSER) {
    return chromium.launch({
      executablePath: process.env.ANIMATION_PIPELINE_BROWSER,
      headless: true,
    });
  }
  throw new Error(
    'No Chromium-family browser found. Install Edge or Chrome, or point ' +
      'ANIMATION_PIPELINE_BROWSER at a Chromium executable.\n' +
      errors.map(line => `  - ${line}`).join('\n'),
  );
}

async function main() {
  // Start from a clean slate so stale frames never leak into packaging.
  rmSync(outputDir, {recursive: true, force: true});
  mkdirSync(outputDir, {recursive: true});

  console.log('[render] starting Vite dev server...');
  const server = await createServer({
    root,
    logLevel: 'warn',
    server: {port: 9425, strictPort: false, open: false},
  });
  await server.listen();
  const url = server.resolvedUrls.local[0];

  console.log(`[render] launching headless browser against ${url}render.html`);
  const browser = await launchBrowser();

  try {
    const page = await browser.newPage();
    page.on('console', message => {
      const source = `${message.location()?.url ?? ''} ${message.text()}`;
      if (message.type() === 'error' && !source.includes('favicon')) {
        console.error(`[browser] ${message.text()}`);
      }
    });
    page.on('pageerror', error => console.error(`[browser] ${error.message}`));

    const varsIndex = process.argv.indexOf('--vars');
    const varsQuery =
      varsIndex >= 0 ? `&vars=${encodeURIComponent(process.argv[varsIndex + 1])}` : '';
    await page.goto(`${url}render.html?project=${projectName}${varsQuery}`, {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForFunction(
      () => window.__renderDone === true || typeof window.__renderError === 'string',
      undefined,
      {timeout: RENDER_TIMEOUT_MS},
    );

    const renderError = await page.evaluate(() => window.__renderError);
    if (renderError) {
      throw new Error(`Motion Canvas render failed:\n${renderError}`);
    }
  } finally {
    await browser.close();
    await server.close();
  }

  if (!existsSync(outputDir)) {
    throw new Error(`Render finished but ${outputDir} does not exist.`);
  }
  const frames = readdirSync(outputDir, {recursive: true}).filter(name =>
    String(name).endsWith('.png'),
  );
  if (frames.length === 0) {
    throw new Error('Render finished but no PNG frames were exported.');
  }
  console.log(`[render] exported ${frames.length} PNG frame(s) to ${outputDir}`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
