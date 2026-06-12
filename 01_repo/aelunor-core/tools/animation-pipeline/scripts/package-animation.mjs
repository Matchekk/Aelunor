/**
 * Generic animation packager: PNG frame sequence -> animated WebP (+ MP4).
 *
 *   node scripts/package-animation.mjs --frames <dir> --name <name>
 *       [--fps 30] [--fuzz 0] [--no-crop] [--pad 4]
 *       [--mp4] [--loops 2] [--runtime]
 *
 * Optimizations applied:
 *  - Frame dedup: consecutive frames that are identical (or whose mean pixel
 *    difference is <= --fuzz, 0-255 scale) are merged into one frame with a
 *    longer delay — animated WebP supports per-frame delays. Hold phases
 *    become nearly free.
 *  - Auto-crop: the canvas is cropped to the union bounding box of visible
 *    pixels across all frames (plus --pad, snapped to even dimensions for
 *    H.264). Disable with --no-crop.
 *
 * Outputs: output/<name>.webp (transparent) and with --mp4 also
 * output/<name>.mp4 (dark backdrop, --loops plays). --runtime additionally
 * copies the WebP to ui/public/brand/animations + app/static mirror.
 */
import {spawnSync} from 'node:child_process';
import {copyFileSync, mkdirSync, readdirSync, rmSync, statSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import ffmpegPath from 'ffmpeg-static';
import sharp from 'sharp';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const coreRoot = resolve(root, '../..');
const RUNTIME_DIR = join(coreRoot, 'ui/public/brand/animations');
const MIRROR_DIR = join(coreRoot, 'app/static/brand/animations');
const BACKGROUND = {r: 22, g: 18, b: 14, alpha: 1};

function getArg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}
const FRAMES_DIR = resolve(root, getArg('frames', 'output/project'));
const NAME = getArg('name', null);
const FPS = Number(getArg('fps', '30'));
const FUZZ = Number(getArg('fuzz', '0'));
const PAD = Number(getArg('pad', '4'));
const LOOPS = Number(getArg('loops', '2'));
const QUALITY = Number(getArg('quality', '88'));
const EFFORT = Number(getArg('effort', '6'));
const CROP = !process.argv.includes('--no-crop');
const MP4 = process.argv.includes('--mp4');
const RUNTIME = process.argv.includes('--runtime');

if (!NAME) {
  console.error('Usage: package-animation.mjs --frames <dir> --name <name> [options]');
  process.exit(1);
}

function meanAbsDiff(a, b) {
  // Sampled; exact equality is checked separately via buffer compare.
  let total = 0;
  let count = 0;
  for (let i = 0; i < a.length; i += 53) {
    total += Math.abs(a[i] - b[i]);
    count++;
  }
  return total / count;
}

async function main() {
  const files = readdirSync(FRAMES_DIR, {recursive: true})
    .map(String)
    .filter(name => name.endsWith('.png'))
    .sort()
    .map(name => join(FRAMES_DIR, name));
  if (files.length === 0) {
    throw new Error(`No PNG frames in ${FRAMES_DIR}`);
  }

  const {width, height} = await sharp(files[0]).metadata();
  const raws = [];
  for (const file of files) {
    raws.push(await sharp(file).ensureAlpha().raw().toBuffer());
  }

  // Dedup consecutive frames into (frame, holdCount) runs.
  const runs = [];
  for (const raw of raws) {
    const last = runs[runs.length - 1];
    if (last && (last.raw.equals(raw) || (FUZZ > 0 && meanAbsDiff(last.raw, raw) <= FUZZ))) {
      last.hold++;
    } else {
      runs.push({raw, hold: 1});
    }
  }

  // Union bounding box of visible pixels across kept frames.
  let region = {left: 0, top: 0, width, height};
  if (CROP) {
    let x0 = width, y0 = height, x1 = -1, y1 = -1;
    for (const {raw} of runs) {
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          if (raw[(y * width + x) * 4 + 3] > 0) {
            if (x < x0) x0 = x;
            if (x > x1) x1 = x;
            if (y < y0) y0 = y;
            if (y > y1) y1 = y;
          }
        }
      }
    }
    if (x1 >= 0) {
      x0 = Math.max(0, x0 - PAD);
      y0 = Math.max(0, y0 - PAD);
      x1 = Math.min(width - 1, x1 + PAD);
      y1 = Math.min(height - 1, y1 + PAD);
      // Even dimensions for H.264.
      let w = x1 - x0 + 1;
      let h = y1 - y0 + 1;
      if (w % 2) w = Math.min(width - x0, w + 1);
      if (h % 2) h = Math.min(height - y0, h + 1);
      region = {left: x0, top: y0, width: w, height: h};
    }
  }

  const frameDelay = 1000 / FPS;
  const delays = runs.map(run => Math.round(run.hold * frameDelay));
  const pngs = await Promise.all(
    runs.map(run =>
      sharp(run.raw, {raw: {width, height, channels: 4}}).extract(region).png().toBuffer(),
    ),
  );

  mkdirSync(join(root, 'output'), {recursive: true});
  const webpTarget = join(root, 'output', `${NAME}.webp`);
  await sharp(pngs, {join: {animated: true}})
    .webp({quality: QUALITY, alphaQuality: 100, effort: EFFORT, loop: 0, delay: delays})
    .toFile(webpTarget);

  console.log(
    `[package] ${webpTarget}\n` +
      `[package]   ${files.length} frames -> ${runs.length} after dedup, ` +
      `${region.width}x${region.height}${CROP ? ` (cropped from ${width}x${height})` : ''}, ` +
      `${(statSync(webpTarget).size / 1024).toFixed(1)} KiB`,
  );

  if (MP4) {
    const flatDir = join(root, 'output', `${NAME}-mp4-frames`);
    rmSync(flatDir, {recursive: true, force: true});
    mkdirSync(flatDir, {recursive: true});
    let index = 0;
    for (let loop = 0; loop < LOOPS; loop++) {
      for (const [r, run] of runs.entries()) {
        const flattened = await sharp(pngs[r]).flatten({background: BACKGROUND}).png().toBuffer();
        for (let hold = 0; hold < run.hold; hold++) {
          await sharp(flattened).toFile(join(flatDir, `${String(index++).padStart(4, '0')}.png`));
        }
      }
    }
    const mp4Target = join(root, 'output', `${NAME}.mp4`);
    const result = spawnSync(
      ffmpegPath,
      ['-y', '-framerate', `${FPS}`, '-i', join(flatDir, '%04d.png'),
       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19',
       '-movflags', '+faststart', mp4Target],
      {stdio: ['ignore', 'ignore', 'pipe'], encoding: 'utf8'},
    );
    if (result.status !== 0) {
      throw new Error(`ffmpeg failed:\n${result.stderr}`);
    }
    rmSync(flatDir, {recursive: true, force: true});
    console.log(
      `[package] ${mp4Target} (${LOOPS}x ${(files.length / FPS).toFixed(1)}s, ` +
        `${(statSync(mp4Target).size / 1024).toFixed(1)} KiB)`,
    );
  }

  if (RUNTIME) {
    for (const dir of [RUNTIME_DIR, MIRROR_DIR]) {
      mkdirSync(dir, {recursive: true});
      copyFileSync(webpTarget, join(dir, `${NAME}.webp`));
      console.log(`[package]   copied -> ${join(dir, `${NAME}.webp`)}`);
    }
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
