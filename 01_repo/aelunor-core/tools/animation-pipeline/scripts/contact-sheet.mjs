/**
 * Renders all frames of an animated WebP/GIF as one contact-sheet PNG so an
 * animation can be reviewed at a glance (also handy for agents).
 *
 *   node scripts/contact-sheet.mjs <animated-file> [columns]
 *
 * Output: ./output/<name>-sheet.png (frames on a checker-free dark backdrop).
 */
import {basename, extname, join} from 'node:path';

import sharp from 'sharp';

const [file, columnsArg] = process.argv.slice(2);
if (!file) {
  console.error('Usage: node scripts/contact-sheet.mjs <animated-file> [columns]');
  process.exit(1);
}

const meta = await sharp(file).metadata();
const pages = meta.pages ?? 1;
const columns = Number(columnsArg) || Math.min(pages, 8);

const frames = [];
for (let page = 0; page < pages; page++) {
  frames.push(
    await sharp(file, {page}).flatten({background: {r: 22, g: 18, b: 14}}).png().toBuffer(),
  );
}

const target = join('output', `${basename(file, extname(file))}-sheet.png`);
await sharp(frames, {join: {across: columns, shim: 4, background: {r: 60, g: 50, b: 40}}})
  .png()
  .toFile(target);
console.log(`[sheet] ${pages} frames -> ${target} (${columns} per row)`);
