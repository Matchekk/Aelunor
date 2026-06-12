import {Img, Rect, makeScene2D} from '@motion-canvas/2d';
import {createRef, usePlayback} from '@motion-canvas/core';

// Single source of truth: the sprite sheet shipped with the UI.
import spriteSheetSrc from '../../../../ui/public/brand/animations/chronicle-book-opening-spritesheet.webp';

const FRAME_COUNT = 5;
const FRAME_SIZE = 512;
/** Matches the Campaign Hub CSS timing: 950ms once-through ≈ 190ms per frame. */
const SECONDS_PER_FRAME = 0.2;
/** Total animation length in render frames (1s at the 30fps render settings). */
const TOTAL_STEPS = 30;

/**
 * Plays the chronicle book opening sprite sheet inside a clipped 512x512
 * viewport. No view fill is set, so the render output keeps a fully
 * transparent background.
 *
 * The sprite index is derived from playback time on every frame instead of
 * counting generator steps: the renderer's step/export cadence has off-by-one
 * quirks at low fps (motion-canvas#1218 area), and time-driven state plus the
 * median-of-window selection in package-assets.mjs is immune to them.
 */
export default makeScene2D(function* (view) {
  const playback = usePlayback();
  const sheet = createRef<Img>();

  view.add(
    <Rect width={FRAME_SIZE} height={FRAME_SIZE} clip>
      <Img
        ref={sheet}
        src={spriteSheetSrc}
        width={FRAME_SIZE * FRAME_COUNT}
        height={FRAME_SIZE}
        smoothing={false}
      />
    </Rect>,
  );

  const showFrameForTime = () => {
    const index = Math.min(
      FRAME_COUNT - 1,
      Math.max(0, Math.floor(playback.time / SECONDS_PER_FRAME + 1e-4)),
    );
    // Shift the sheet so the clipped viewport shows the frame at `index`.
    sheet().position.x((FRAME_SIZE * (FRAME_COUNT - 1)) / 2 - FRAME_SIZE * index);
  };

  for (let step = 0; step < TOTAL_STEPS; step++) {
    showFrameForTime();
    yield;
  }
});
