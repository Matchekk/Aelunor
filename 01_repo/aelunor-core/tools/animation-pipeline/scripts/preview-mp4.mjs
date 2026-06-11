/**
 * Builds an MP4 preview of the shipped animated WebP so the animation can be
 * reviewed in any video player. H.264 has no alpha channel, so frames are
 * composited onto a dark hub-like background first.
 *
 * Output (preview artifact, not a runtime asset):
 *   ./output/chronicle-book-opening-preview.mp4
 */
import {spawnSync} from 'node:child_process';
import {mkdirSync, rmSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

import ffmpegPath from 'ffmpeg-static';
import sharp from 'sharp';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const coreRoot = resolve(root, '../..');

const ANIMATED_WEBP = join(
  coreRoot,
  'ui/public/brand/animations/chronicle-book-opening-animated.webp',
);
const framesDir = join(root, 'output', 'preview-frames');
const target = join(root, 'output', 'chronicle-book-opening-preview.mp4');

const FRAME_COUNT = 5;
const FRAME_DELAY_MS = 190;
const LOOPS = 3;
const BACKGROUND = {r: 22, g: 18, b: 14, alpha: 1};

async function main() {
  rmSync(framesDir, {recursive: true, force: true});
  mkdirSync(framesDir, {recursive: true});

  // Decode the shipped asset itself so the preview shows exactly what the UI gets.
  const flattened = [];
  for (let page = 0; page < FRAME_COUNT; page++) {
    flattened.push(
      await sharp(ANIMATED_WEBP, {page}).flatten({background: BACKGROUND}).png().toBuffer(),
    );
  }
  for (let loop = 0; loop < LOOPS; loop++) {
    for (let page = 0; page < FRAME_COUNT; page++) {
      const index = loop * FRAME_COUNT + page;
      await sharp(flattened[page]).toFile(
        join(framesDir, `${String(index).padStart(3, '0')}.png`),
      );
    }
  }

  const result = spawnSync(
    ffmpegPath,
    [
      '-y',
      '-framerate', `1000/${FRAME_DELAY_MS}`,
      '-i', join(framesDir, '%03d.png'),
      '-c:v', 'libx264',
      '-pix_fmt', 'yuv420p',
      '-crf', '20',
      '-movflags', '+faststart',
      target,
    ],
    {stdio: ['ignore', 'ignore', 'pipe']},
  );
  if (result.status !== 0) {
    throw new Error(`ffmpeg failed:\n${result.stderr}`);
  }
  console.log(`[preview] ${target}`);
  console.log(
    `[preview] ${FRAME_COUNT * LOOPS} frames (${LOOPS} loops) at ${FRAME_DELAY_MS}ms/frame`,
  );
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
