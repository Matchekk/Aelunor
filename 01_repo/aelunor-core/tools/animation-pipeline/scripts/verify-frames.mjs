/**
 * Optional sanity check: confirms that the frames selected from ./output by
 * the packaging step match sprite frames 0..4 of the source sheet
 * (pixel-sampled mean absolute difference; a match is well below 2.0).
 */
import {readdirSync} from 'node:fs';
import {join} from 'node:path';

import sharp from 'sharp';

const SRC = '../../ui/public/brand/animations/chronicle-book-opening-spritesheet.webp';

const refs = [];
for (let i = 0; i < 5; i++) {
  refs.push(
    await sharp(SRC)
      .extract({left: i * 512, top: 0, width: 512, height: 512})
      .ensureAlpha()
      .raw()
      .toBuffer(),
  );
}

const sequence = readdirSync(join('output', 'project'), {recursive: true})
  .map(String)
  .filter(name => name.endsWith('.png'))
  .sort()
  .map(name => join('output', 'project', name));
const selected = Array.from({length: 5}, (_, index) =>
  sequence[Math.floor(((index + 0.5) * sequence.length) / 5)],
);

for (const [n, path] of selected.entries()) {
  const rendered = await sharp(path).ensureAlpha().raw().toBuffer();
  const diffs = refs.map(ref => {
    let total = 0;
    for (let i = 0; i < ref.length; i += 97) {
      total += Math.abs(ref[i] - rendered[i]);
    }
    return total / Math.ceil(ref.length / 97);
  });
  const best = diffs.indexOf(Math.min(...diffs));
  console.log(
    `selected[${n}] = ${path} -> sprite frame ${best} (diff ${diffs[best].toFixed(2)})`,
  );
}
