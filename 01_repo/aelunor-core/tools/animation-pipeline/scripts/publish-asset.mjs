/**
 * Publishes a finished asset into the right Aelunor folders:
 *
 *   node scripts/publish-asset.mjs <file...> [--kind <kind>] [--as <filename>]
 *       [--dry-run]
 *
 * For each file this:
 *   1. copies it to ui/public/brand/<kind>/<name>   (".clean"/".min" suffixes
 *      from the refine/compress tools are stripped automatically)
 *   2. mirrors it to app/static/brand/<kind>/<name>
 *   3. registers it in aelunor.asset-manifest.json if missing (with a
 *      review-me note — allowedUsage should be curated by a human)
 *   4. runs scripts/check_ui_asset_usage.py as a final gate
 *
 * --kind: animations | illustrations | icons | wallpapers | ui-kit.
 * Default: animated images -> animations, everything else -> illustrations.
 */
import {spawnSync} from 'node:child_process';
import {copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync} from 'node:fs';
import {basename, dirname, extname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import sharp from 'sharp';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const coreRoot = resolve(root, '../..');
const MANIFEST = join(coreRoot, 'ui/src/shared/design/aelunor.asset-manifest.json');

const ROLE_BY_KIND = {
  animations: 'animation',
  illustrations: 'illustration',
  icons: 'icon',
  wallpapers: 'background',
  'ui-kit': 'unknown',
};

function getArg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}
const KIND_ARG = getArg('kind', null);
const AS = getArg('as', null);
const DRY = process.argv.includes('--dry-run');
const files = process.argv.slice(2).filter(arg => !arg.startsWith('--') && arg !== KIND_ARG && arg !== AS);

if (files.length === 0) {
  console.error('Usage: publish-asset.mjs <file...> [--kind animations|illustrations|icons|wallpapers|ui-kit] [--as name] [--dry-run]');
  process.exit(1);
}
if (KIND_ARG && !(KIND_ARG in ROLE_BY_KIND)) {
  console.error(`Unknown --kind "${KIND_ARG}". Use: ${Object.keys(ROLE_BY_KIND).join(', ')}`);
  process.exit(1);
}
if (AS && files.length > 1) {
  console.error('--as only works with a single input file.');
  process.exit(1);
}

function cleanName(file) {
  // test-cutout.clean.png -> test-cutout.png; foo.min.webp -> foo.webp
  const ext = extname(file);
  let stem = basename(file, ext);
  for (const suffix of ['.clean', '.min']) {
    if (stem.endsWith(suffix)) {
      stem = stem.slice(0, -suffix.length);
    }
  }
  return `${stem}${ext}`;
}

function registerInManifest(id, kind, name, animated) {
  const manifest = JSON.parse(readFileSync(MANIFEST, 'utf8'));
  if (manifest.assets.some(asset => asset.id === id)) {
    return 'already registered';
  }
  manifest.assets.push({
    id,
    path: `/brand/${kind}/${name}`,
    mirroredPath: `/static/brand/${kind}/${name}`,
    category: kind === 'wallpapers' ? 'wallpaper' : 'ui-kit',
    role: ROLE_BY_KIND[kind],
    allowedUsage: ['decorative visual (review and narrow this down)'],
    forbiddenUsage: ['semantic navigation icon', 'text replacement', 'standalone brand logo'],
    intendedComponent: 'TBD',
    layer: 'content',
    accessibility:
      'Decorative asset: render with alt="" / aria-hidden="true" unless it carries meaning.',
    responsiveBehavior: 'Preserve aspect ratio; avoid layout shift.',
    notes: `Published via tools/animation-pipeline publish-asset${animated ? ' (animated)' : ''}. Review allowedUsage/intendedComponent.`,
  });
  writeFileSync(MANIFEST, `${JSON.stringify(manifest, null, 2)}\n`);
  return 'registered (review allowedUsage)';
}

let failed = false;
for (const file of files) {
  const source = resolve(process.cwd(), file);
  if (!existsSync(source)) {
    console.error(`[publish] not found: ${source}`);
    failed = true;
    continue;
  }
  const meta = await sharp(source).metadata();
  const animated = (meta.pages ?? 1) > 1;
  const kind = KIND_ARG ?? (animated ? 'animations' : 'illustrations');
  const name = AS ?? cleanName(source);
  const id = basename(name, extname(name));

  const targets = [
    join(coreRoot, 'ui/public/brand', kind, name),
    join(coreRoot, 'app/static/brand', kind, name),
  ];
  console.log(`[publish] ${basename(source)} -> brand/${kind}/${name}${DRY ? ' (dry-run)' : ''}`);
  if (DRY) {
    continue;
  }
  for (const target of targets) {
    mkdirSync(dirname(target), {recursive: true});
    copyFileSync(source, target);
    console.log(`[publish]   ${target}`);
  }
  console.log(`[publish]   manifest: ${registerInManifest(id, kind, name, animated)}`);
}

if (!DRY) {
  const check = spawnSync('python', [join(coreRoot, 'scripts/check_ui_asset_usage.py')], {
    cwd: coreRoot,
    stdio: 'inherit',
  });
  if (check.status !== 0) {
    failed = true;
  }
}
process.exit(failed ? 1 : 0);
