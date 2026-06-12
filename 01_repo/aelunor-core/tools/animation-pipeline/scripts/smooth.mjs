/**
 * Frame interpolation: generates in-between frames so a low-frame-count
 * animation plays smoothly, while keeping the alpha channel intact.
 *
 *   node scripts/smooth.mjs [--mode blend|motion] [--multiply N] [--loop] [--runtime]
 *
 * Modes:
 *   blend   (default) Alpha-aware crossfade between consecutive frames, pure
 *           sharp/JS. Artifact-free but big movements show ghosting.
 *   motion  Real motion interpolation via ffmpeg's minterpolate filter.
 *           H.264 filters cannot handle alpha, so color (premultiplied on
 *           black) and the alpha matte are interpolated as two separate
 *           streams and recombined per pixel afterwards.
 *
 * --multiply N  in-between frames per source frame in blend mode (default 6).
 * --loop        also interpolate from the last frame back to the first, for
 *               seamless infinite looping (default off: play-once character).
 * --runtime     additionally copy the result to ui/public + app/static.
 *
 * Output: ./output/chronicle-book-opening-animated-smooth.webp
 * Total duration always stays at 950ms (the Campaign Hub timing).
 */
import {spawnSync} from 'node:child_process';
import {copyFileSync, mkdirSync, readdirSync, rmSync, statSync} from 'node:fs';
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
const RUNTIME_DIR = join(coreRoot, 'ui/public/brand/animations');
const MIRROR_DIR = join(coreRoot, 'app/static/brand/animations');
const OUTPUT_NAME = 'chronicle-book-opening-animated-smooth.webp';

const SIZE = 512;
const FRAME_COUNT = 5;
const TOTAL_MS = 950;
const WEBP_OPTIONS = {quality: 90, alphaQuality: 100, effort: 6};

function getArg(name, fallback) {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : fallback;
}
const MODE = getArg('mode', 'blend');
const MULTIPLY = Number(getArg('multiply', '6'));
const LOOP = process.argv.includes('--loop');
const RUNTIME = process.argv.includes('--runtime');

async function loadBaseFrames() {
  const frames = [];
  for (let page = 0; page < FRAME_COUNT; page++) {
    frames.push(
      await sharp(ANIMATED_WEBP, {page}).ensureAlpha().raw().toBuffer(),
    );
  }
  if (LOOP) {
    frames.push(frames[0]);
  }
  return frames;
}

/** Lerp two straight-alpha RGBA buffers in premultiplied space. */
function blendFrames(a, b, t) {
  const out = Buffer.alloc(a.length);
  for (let i = 0; i < a.length; i += 4) {
    const alphaA = a[i + 3];
    const alphaB = b[i + 3];
    const alpha = alphaA + (alphaB - alphaA) * t;
    out[i + 3] = Math.round(alpha);
    for (let c = 0; c < 3; c++) {
      const premultA = (a[i + c] * alphaA) / 255;
      const premultB = (b[i + c] * alphaB) / 255;
      const premult = premultA + (premultB - premultA) * t;
      out[i + c] = alpha > 0 ? Math.min(255, Math.round((premult * 255) / alpha)) : 0;
    }
  }
  return out;
}

async function interpolateBlend(base) {
  const frames = [];
  for (let gap = 0; gap < base.length - 1; gap++) {
    for (let step = 0; step < MULTIPLY; step++) {
      frames.push(blendFrames(base[gap], base[gap + 1], step / MULTIPLY));
    }
  }
  if (!LOOP) {
    frames.push(base[base.length - 1]);
  }
  return frames;
}

async function interpolateMotion(base) {
  const tmp = join(root, 'output', 'smooth-tmp');
  const dirs = {
    color: join(tmp, 'color'),
    alpha: join(tmp, 'alpha'),
    colorOut: join(tmp, 'color-out'),
    alphaOut: join(tmp, 'alpha-out'),
  };
  rmSync(tmp, {recursive: true, force: true});
  Object.values(dirs).forEach(dir => mkdirSync(dir, {recursive: true}));

  // ffmpeg's minterpolate cannot extrapolate past the last input frame and
  // truncates the tail, so hold the final frame once more at the end.
  const inputs = [...base, base[base.length - 1]];

  // Split each frame into premultiplied-on-black color and an alpha matte.
  for (const [index, frame] of inputs.entries()) {
    const color = Buffer.alloc((frame.length / 4) * 3);
    const alpha = Buffer.alloc(frame.length / 4);
    for (let p = 0; p < alpha.length; p++) {
      alpha[p] = frame[p * 4 + 3];
      for (let c = 0; c < 3; c++) {
        color[p * 3 + c] = (frame[p * 4 + c] * alpha[p]) / 255;
      }
    }
    const name = `${String(index).padStart(3, '0')}.png`;
    await sharp(color, {raw: {width: SIZE, height: SIZE, channels: 3}})
      .png()
      .toFile(join(dirs.color, name));
    await sharp(alpha, {raw: {width: SIZE, height: SIZE, channels: 1}})
      .png()
      .toFile(join(dirs.alpha, name));
  }

  const inputFps = `${(inputs.length * 1000) / TOTAL_MS}`;
  for (const [input, output] of [
    [dirs.color, dirs.colorOut],
    [dirs.alpha, dirs.alphaOut],
  ]) {
    const result = spawnSync(
      ffmpegPath,
      [
        '-y',
        '-framerate', inputFps,
        '-i', join(input, '%03d.png'),
        '-vf', 'minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
        join(output, '%03d.png'),
      ],
      {stdio: ['ignore', 'ignore', 'pipe'], encoding: 'utf8'},
    );
    if (result.status !== 0) {
      throw new Error(`ffmpeg minterpolate failed:\n${result.stderr}`);
    }
  }

  // Recombine the two interpolated streams into straight-alpha RGBA.
  const names = readdirSync(dirs.colorOut).sort();
  const frames = [];
  for (const name of names) {
    const color = await sharp(join(dirs.colorOut, name))
      .removeAlpha()
      .raw()
      .toBuffer();
    const alpha = await sharp(join(dirs.alphaOut, name))
      .greyscale()
      .raw()
      .toBuffer();
    const frame = Buffer.alloc(alpha.length * 4);
    for (let p = 0; p < alpha.length; p++) {
      frame[p * 4 + 3] = alpha[p];
      for (let c = 0; c < 3; c++) {
        frame[p * 4 + c] =
          alpha[p] > 0
            ? Math.min(255, Math.round((color[p * 3 + c] * 255) / alpha[p]))
            : 0;
      }
    }
    frames.push(frame);
  }
  rmSync(tmp, {recursive: true, force: true});
  // Guarantee the animation lands exactly on the true final frame.
  frames.push(base[base.length - 1]);
  return frames;
}

async function main() {
  if (!['blend', 'motion'].includes(MODE)) {
    throw new Error(`Unknown --mode "${MODE}"; use blend or motion.`);
  }
  console.log(`[smooth] mode=${MODE} loop=${LOOP}`);
  const base = await loadBaseFrames();
  const frames = MODE === 'blend' ? await interpolateBlend(base) : await interpolateMotion(base);
  const delay = Math.round(TOTAL_MS / frames.length);

  const target = join(root, 'output', OUTPUT_NAME);
  const pngFrames = await Promise.all(
    frames.map(frame =>
      sharp(frame, {raw: {width: SIZE, height: SIZE, channels: 4}}).png().toBuffer(),
    ),
  );
  await sharp(pngFrames, {join: {animated: true}})
    .webp({...WEBP_OPTIONS, loop: 0, delay})
    .toFile(target);

  const kib = (statSync(target).size / 1024).toFixed(1);
  console.log(`[smooth] ${target}`);
  console.log(`[smooth]   ${frames.length} frames at ${delay}ms (~${TOTAL_MS}ms total), ${kib} KiB`);

  if (RUNTIME) {
    for (const dir of [RUNTIME_DIR, MIRROR_DIR]) {
      mkdirSync(dir, {recursive: true});
      copyFileSync(target, join(dir, OUTPUT_NAME));
      console.log(`[smooth]   copied -> ${join(dir, OUTPUT_NAME)}`);
    }
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
