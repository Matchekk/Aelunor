/**
 * Standalone asset compression tool (sharp-based, animation-aware).
 *
 *   node scripts/compress.mjs <file...> [options]
 *
 * Options:
 *   --quality N        WebP quality 1-100 (default 82)
 *   --alpha-quality N  alpha channel quality (default 100)
 *   --effort N         encoder effort 0-6 (default 6, slowest/smallest)
 *   --lossless         lossless WebP instead of lossy
 *   --max-width N      downscale if wider than N px (aspect preserved)
 *   --out <dir>        write results to this directory
 *   --replace          overwrite the input file (input must be .webp)
 *
 * Without --out/--replace, results are written next to the input as
 * <name>.min.webp. Animated inputs (animated WebP/GIF) keep all their frames
 * and timing. Prints before/after sizes; skips results that would be larger.
 */
import {mkdirSync, statSync} from 'node:fs';
import {basename, dirname, extname, join} from 'node:path';

import sharp from 'sharp';

const args = process.argv.slice(2);
const files = [];
const options = {
  quality: 82,
  alphaQuality: 100,
  effort: 6,
  lossless: false,
  maxWidth: null,
  out: null,
  replace: false,
};

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case '--quality': options.quality = Number(args[++i]); break;
    case '--alpha-quality': options.alphaQuality = Number(args[++i]); break;
    case '--effort': options.effort = Number(args[++i]); break;
    case '--lossless': options.lossless = true; break;
    case '--max-width': options.maxWidth = Number(args[++i]); break;
    case '--out': options.out = args[++i]; break;
    case '--replace': options.replace = true; break;
    default: files.push(args[i]);
  }
}

if (files.length === 0) {
  console.error('Usage: node scripts/compress.mjs <file...> [--quality N] [--lossless] [--max-width N] [--out dir] [--replace]');
  process.exit(1);
}

function targetPath(file) {
  if (options.replace) {
    if (extname(file).toLowerCase() !== '.webp') {
      throw new Error(`--replace requires a .webp input, got: ${file}`);
    }
    return file;
  }
  const name = `${basename(file, extname(file))}.min.webp`;
  return join(options.out ?? dirname(file), name);
}

async function compress(file) {
  const before = statSync(file).size;
  const probe = await sharp(file).metadata();
  const animated = (probe.pages ?? 1) > 1;

  let image = sharp(file, {animated});
  if (options.maxWidth && probe.width > options.maxWidth) {
    image = image.resize({width: options.maxWidth});
  }
  const buffer = await image
    .webp({
      quality: options.quality,
      alphaQuality: options.alphaQuality,
      effort: options.effort,
      lossless: options.lossless,
      // Preserve original loop/delay metadata for animated inputs.
      ...(animated ? {loop: probe.loop ?? 0, delay: probe.delay} : {}),
    })
    .toBuffer();

  const target = targetPath(file);
  const sameFile = target === file;
  if (buffer.length >= before && sameFile) {
    console.log(`[compress] ${file}: already optimal (${(before / 1024).toFixed(1)} KiB), skipped`);
    return;
  }

  if (options.out) {
    mkdirSync(options.out, {recursive: true});
  }
  await sharp(buffer, {animated}).toFile(target);
  const after = statSync(target).size;
  const saved = (((before - after) / before) * 100).toFixed(1);
  console.log(
    `[compress] ${file} (${(before / 1024).toFixed(1)} KiB) -> ${target} ` +
      `(${(after / 1024).toFixed(1)} KiB, ${saved}% smaller${animated ? `, ${probe.pages} frames kept` : ''})`,
  );
}

for (const file of files) {
  await compress(file);
}
