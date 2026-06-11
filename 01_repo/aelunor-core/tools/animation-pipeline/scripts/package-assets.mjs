/**
 * Packages rendered frames into the runtime animation assets:
 *
 *   chronicle-book-opening-animated.webp                (animated WebP, 5 pages)
 *   chronicle-book-opening-spritesheet-normalized.webp  (2560x512 sprite sheet)
 *
 * Frame source, in order of preference:
 *   1. PNG sequence rendered by Motion Canvas (./output)
 *   2. --from-spritesheet: slices the source sprite sheet directly with sharp
 *      (fallback that needs no browser at all)
 *
 * Outputs are written to ui/public/brand/animations and mirrored to
 * app/static/brand/animations.
 */
import {copyFileSync, existsSync, mkdirSync, readdirSync, statSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import sharp from 'sharp';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const coreRoot = resolve(root, '../..');
const outputDir = join(root, 'output', 'project');

const SOURCE_SPRITESHEET = join(
  coreRoot,
  'ui/public/brand/animations/chronicle-book-opening-spritesheet.webp',
);
const RUNTIME_DIR = join(coreRoot, 'ui/public/brand/animations');
const MIRROR_DIR = join(coreRoot, 'app/static/brand/animations');

const FRAME_SIZE = 512;
const FRAME_COUNT = 5;
/** Matches the Campaign Hub CSS once-through timing (950ms / 5 frames). */
const FRAME_DELAY_MS = 190;
const WEBP_OPTIONS = {quality: 90, alphaQuality: 100, effort: 6};

function collectRenderedFrames() {
  if (!existsSync(outputDir)) {
    return [];
  }
  const sequence = readdirSync(outputDir, {recursive: true})
    .map(String)
    .filter(name => name.endsWith('.png'))
    .sort()
    .map(name => join(outputDir, name));
  if (sequence.length < FRAME_COUNT) {
    return sequence;
  }
  // The scene oversamples each sprite frame; pick the median render frame of
  // each window so off-by-one drift at window boundaries cannot matter.
  return Array.from({length: FRAME_COUNT}, (_, index) => {
    return sequence[Math.floor(((index + 0.5) * sequence.length) / FRAME_COUNT)];
  });
}

async function framesFromRender(paths) {
  return Promise.all(
    paths.map(path =>
      sharp(path)
        .resize(FRAME_SIZE, FRAME_SIZE, {fit: 'contain', background: {r: 0, g: 0, b: 0, alpha: 0}})
        .ensureAlpha()
        .png()
        .toBuffer(),
    ),
  );
}

async function framesFromSpritesheet() {
  const meta = await sharp(SOURCE_SPRITESHEET).metadata();
  if (meta.width !== FRAME_SIZE * FRAME_COUNT || meta.height !== FRAME_SIZE) {
    throw new Error(
      `Expected ${FRAME_SIZE * FRAME_COUNT}x${FRAME_SIZE} sprite sheet, got ${meta.width}x${meta.height}`,
    );
  }
  return Promise.all(
    Array.from({length: FRAME_COUNT}, (_, index) =>
      sharp(SOURCE_SPRITESHEET)
        .extract({left: index * FRAME_SIZE, top: 0, width: FRAME_SIZE, height: FRAME_SIZE})
        .ensureAlpha()
        .png()
        .toBuffer(),
    ),
  );
}

async function writeAnimatedWebp(frames, target) {
  await sharp(frames, {join: {animated: true}})
    .webp({...WEBP_OPTIONS, loop: 0, delay: FRAME_DELAY_MS})
    .toFile(target);
}

async function writeNormalizedSpritesheet(frames, target) {
  await sharp(frames, {join: {across: FRAME_COUNT, shim: 0}})
    .webp(WEBP_OPTIONS)
    .toFile(target);
}

async function describe(path) {
  const meta = await sharp(path, {animated: true}).metadata();
  const kib = (statSync(path).size / 1024).toFixed(1);
  const pages = meta.pages && meta.pages > 1 ? `, ${meta.pages} pages` : '';
  return `${meta.width}x${meta.pageHeight ?? meta.height}${pages}, alpha=${meta.hasAlpha}, ${kib} KiB`;
}

async function main() {
  const fromSpritesheet = process.argv.includes('--from-spritesheet');

  let frames;
  if (!fromSpritesheet) {
    const rendered = collectRenderedFrames();
    if (rendered.length === FRAME_COUNT) {
      console.log(`[package] using ${rendered.length} Motion Canvas frames from ./output`);
      frames = await framesFromRender(rendered);
    } else if (rendered.length > 0) {
      throw new Error(
        `Expected ${FRAME_COUNT} rendered frames, found ${rendered.length}. ` +
          'Re-run "npm run render" or use "npm run package -- --from-spritesheet".',
      );
    }
  }
  if (!frames) {
    console.log('[package] slicing source sprite sheet directly (no rendered frames)');
    frames = await framesFromSpritesheet();
  }

  mkdirSync(RUNTIME_DIR, {recursive: true});
  mkdirSync(MIRROR_DIR, {recursive: true});

  const animated = join(RUNTIME_DIR, 'chronicle-book-opening-animated.webp');
  const normalized = join(RUNTIME_DIR, 'chronicle-book-opening-spritesheet-normalized.webp');

  await writeAnimatedWebp(frames, animated);
  await writeNormalizedSpritesheet(frames, normalized);

  for (const file of [animated, normalized]) {
    const mirrored = join(MIRROR_DIR, file.split(/[\\/]/).pop());
    copyFileSync(file, mirrored);
    console.log(`[package] ${file}`);
    console.log(`[package]   ${await describe(file)}`);
    console.log(`[package]   mirrored -> ${mirrored}`);
  }
  console.log('[package] done');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
