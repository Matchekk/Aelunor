/**
 * One-command animation from any Aelunor asset — no scene code required:
 *
 *   node scripts/animate.mjs --asset <png> [--preset reveal|idle|pulse|glint]
 *       [--name <output-name>] [--glow '#46d2ff'] [--asset-size 380]
 *       [--fuzz 0.4] [--mp4] [--runtime] [--open]
 *
 * Renders src/scenes/presetScene.tsx headlessly with the given parameters
 * (passed as Motion Canvas project variables) and packages the frames via
 * package-animation.mjs (dedup + auto-crop). The asset must live inside
 * aelunor-core (it is served through Vite's /@fs/).
 *
 * Examples:
 *   node scripts/animate.mjs --asset ../../ui/public/brand/aelunor-icon-512x512.png
 *   node scripts/animate.mjs --asset ...icon.png --preset idle --runtime
 */
import {spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {basename, dirname, extname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const coreRoot = resolve(root, '../..');

function getArg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}

const assetArg = getArg('asset', null);
const preset = getArg('preset', 'reveal');
const glowColor = getArg('glow', '#46d2ff');
const assetSize = Number(getArg('asset-size', '380'));
const fuzz = getArg('fuzz', '0.4');

if (!assetArg) {
  console.error('Usage: animate.mjs --asset <png> [--preset reveal|idle|pulse|glint] [options]');
  process.exit(1);
}
const asset = resolve(process.cwd(), assetArg);
if (!existsSync(asset)) {
  console.error(`Asset not found: ${asset}`);
  process.exit(1);
}
if (relative(coreRoot, asset).startsWith('..')) {
  console.error(`Asset must live inside aelunor-core (${coreRoot}) to be served via /@fs/.`);
  process.exit(1);
}

const name = getArg('name', `${basename(asset, extname(asset))}-${preset}`);
const assetUrl = `/@fs/${asset.replace(/\\/g, '/')}`;
const vars = JSON.stringify({asset: assetUrl, preset, glowColor, assetSize});

function run(args) {
  const result = spawnSync(process.execPath, args, {cwd: root, stdio: 'inherit'});
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log(`[animate] ${basename(asset)} preset=${preset} -> ${name}`);
run([
  join(root, 'scripts/render-headless.mjs'),
  '--project', 'presetProject',
  '--vars', vars,
]);

const packageArgs = [
  join(root, 'scripts/package-animation.mjs'),
  '--frames', 'output/presetProject',
  '--name', name,
  '--fuzz', fuzz,
];
for (const flag of ['--mp4', '--runtime']) {
  if (process.argv.includes(flag)) {
    packageArgs.push(flag);
  }
}
run(packageArgs);

if (process.argv.includes('--open')) {
  const target = join(root, 'output', `${name}${process.argv.includes('--mp4') ? '.mp4' : '.webp'}`);
  spawnSync('cmd', ['/c', 'start', '', target], {stdio: 'ignore'});
}
