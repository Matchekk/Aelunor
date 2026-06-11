import {Circle, Gradient, Img, Node, Rect, makeScene2D} from '@motion-canvas/2d';
import {
  all,
  chain,
  createRef,
  easeInOutCubic,
  easeInOutSine,
  easeOutCubic,
  linear,
  waitFor,
} from '@motion-canvas/core';

import logoSrc from '../../../../ui/public/brand/aelunor-icon-512x512.png';

const LOGO_SIZE = 380;
const GLOW_COLOR = '#46d2ff';

/**
 * Aelunor logo reveal (~4.5s, 512x512, transparent):
 * the emblem floats in over a soft ground shadow, an anime-style light glint
 * sweeps across it once, the central obelisk glow pulses and settles to a
 * subtle shimmer, then the emblem hovers gently while the ground shadow
 * counters the motion. Deliberately restrained — no shakes, no flares.
 */
export default makeScene2D(function* (view) {
  const emblem = createRef<Node>();
  const logo = createRef<Node>();
  const glow = createRef<Img>();
  const glint = createRef<Rect>();
  const ground = createRef<Circle>();

  const glintFill = new Gradient({
    type: 'linear',
    from: [-70, 0],
    to: [70, 0],
    stops: [
      {offset: 0, color: 'rgba(255,255,255,0)'},
      {offset: 0.5, color: 'rgba(235,248,255,0.85)'},
      {offset: 1, color: 'rgba(255,255,255,0)'},
    ],
  });
  const groundFill = new Gradient({
    type: 'radial',
    from: [0, 0],
    to: [0, 0],
    fromRadius: 0,
    toRadius: 110,
    stops: [
      {offset: 0, color: 'rgba(0,0,0,0.55)'},
      {offset: 1, color: 'rgba(0,0,0,0)'},
    ],
  });

  view.add(
    <>
      <Circle
        ref={ground}
        y={196}
        width={230}
        height={56}
        fill={groundFill}
        opacity={0}
        scale={[0.7, 1]}
      />
      <Node ref={emblem}>
        <Img
          ref={glow}
          src={logoSrc}
          width={LOGO_SIZE}
          height={LOGO_SIZE}
          opacity={0}
          shadowColor={GLOW_COLOR}
          shadowBlur={0}
        />
        <Node ref={logo} cache opacity={0} y={26} scale={0.94}>
          <Img src={logoSrc} width={LOGO_SIZE} height={LOGO_SIZE} />
          <Rect
            ref={glint}
            width={150}
            height={720}
            rotation={22}
            x={-360}
            opacity={0}
            fill={glintFill}
            compositeOperation={'source-atop'}
          />
        </Node>
      </Node>
    </>,
  );

  // Float in over the forming ground shadow.
  yield* all(
    logo().opacity(1, 0.7, easeOutCubic),
    logo().position.y(0, 0.9, easeOutCubic),
    logo().scale(1, 0.9, easeOutCubic),
    ground().opacity(0.5, 0.9, easeOutCubic),
    ground().scale.x(1, 0.9, easeOutCubic),
  );
  yield* waitFor(0.15);

  // Anime-style glint sweeps across the emblem once.
  yield* all(
    glint().position.x(360, 0.8, linear),
    chain(
      glint().opacity(0.6, 0.2, easeInOutCubic),
      waitFor(0.35),
      glint().opacity(0, 0.25, easeInOutCubic),
    ),
  );

  // The obelisk glow breathes once, then settles to a subtle shimmer;
  // the hover starts while the glow is fading.
  yield* all(
    chain(
      all(glow().opacity(0.85, 0.5, easeInOutCubic), glow().shadowBlur(46, 0.5, easeInOutCubic)),
      all(glow().opacity(0.22, 0.7, easeInOutCubic), glow().shadowBlur(14, 0.7, easeInOutCubic)),
    ),
    chain(
      waitFor(0.4),
      all(
        emblem().position.y(-7, 0.8, easeInOutSine),
        ground().scale.x(0.92, 0.8, easeInOutSine),
        ground().opacity(0.4, 0.8, easeInOutSine),
      ),
    ),
  );

  // Settle back down; shadow follows.
  yield* all(
    emblem().position.y(0, 0.9, easeInOutSine),
    ground().scale.x(1, 0.9, easeInOutSine),
    ground().opacity(0.5, 0.9, easeInOutSine),
  );
  yield* waitFor(0.3);
});
