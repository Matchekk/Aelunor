import {Circle, Gradient, Img, Node, Rect, makeScene2D} from '@motion-canvas/2d';
import {
  all,
  chain,
  createRef,
  easeInOutCubic,
  easeInOutSine,
  easeOutCubic,
  linear,
  useScene,
  waitFor,
} from '@motion-canvas/core';

/**
 * Parameterized animation scene driven by project variables (set per render
 * by scripts/animate.mjs — no code changes needed for new assets):
 *
 *   asset      URL of the source image (served via /@fs/)
 *   preset     reveal | idle | pulse | glint
 *   glowColor  accent glow color (default Aelunor cyan)
 *   assetSize  rendered asset edge length in px (default 380)
 *
 * Presets:
 *   reveal  float-in over a forming ground shadow, glint sweep, glow pulse,
 *           gentle hover — the full intro (same look as the logo reveal).
 *   idle    seamless hover loop with shadow counter-motion and subtle glow
 *           shimmer; first frame == last frame, loops forever.
 *   pulse   seamless glow-breathing loop, no movement.
 *   glint   a single light sweep, for short hover/attention moments.
 */
export default makeScene2D(function* (view) {
  const variables = useScene().variables;
  const asset = variables.get('asset', '')();
  const preset = variables.get('preset', 'reveal')();
  const glowColor = variables.get('glowColor', '#46d2ff')();
  const assetSize = variables.get('assetSize', 380)();
  if (!asset) {
    throw new Error('presetScene requires the "asset" variable');
  }

  const emblem = createRef<Node>();
  const logo = createRef<Node>();
  const glow = createRef<Img>();
  const glint = createRef<Rect>();
  const ground = createRef<Circle>();

  const glintFill = new Gradient({
    type: 'linear',
    from: [-assetSize * 0.18, 0],
    to: [assetSize * 0.18, 0],
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
    toRadius: assetSize * 0.29,
    stops: [
      {offset: 0, color: 'rgba(0,0,0,0.55)'},
      {offset: 1, color: 'rgba(0,0,0,0)'},
    ],
  });
  const glintSpan = assetSize * 0.95;

  view.add(
    <>
      <Circle
        ref={ground}
        y={assetSize / 2 + 6}
        width={assetSize * 0.6}
        height={assetSize * 0.15}
        fill={groundFill}
        opacity={0}
        scale={[0.7, 1]}
      />
      <Node ref={emblem}>
        <Img
          ref={glow}
          src={asset}
          width={assetSize}
          height={assetSize}
          opacity={0}
          shadowColor={glowColor}
          shadowBlur={0}
        />
        <Node ref={logo} cache opacity={0} y={26} scale={0.94}>
          <Img src={asset} width={assetSize} height={assetSize} />
          <Rect
            ref={glint}
            width={assetSize * 0.4}
            height={assetSize * 1.9}
            rotation={22}
            x={-glintSpan}
            opacity={0}
            fill={glintFill}
            compositeOperation={'source-atop'}
          />
        </Node>
      </Node>
    </>,
  );

  const atRest = () => {
    logo().opacity(1);
    logo().position.y(0);
    logo().scale(1);
    ground().opacity(0.5);
    ground().scale.x(1);
  };

  function* glintSweep(strength = 0.6) {
    glint().position.x(-glintSpan);
    yield* all(
      glint().position.x(glintSpan, 0.8, linear),
      chain(
        glint().opacity(strength, 0.2, easeInOutCubic),
        waitFor(0.35),
        glint().opacity(0, 0.25, easeInOutCubic),
      ),
    );
  }

  switch (preset) {
    case 'reveal': {
      yield* all(
        logo().opacity(1, 0.7, easeOutCubic),
        logo().position.y(0, 0.9, easeOutCubic),
        logo().scale(1, 0.9, easeOutCubic),
        ground().opacity(0.5, 0.9, easeOutCubic),
        ground().scale.x(1, 0.9, easeOutCubic),
      );
      yield* waitFor(0.15);
      yield* glintSweep();
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
      yield* all(
        emblem().position.y(0, 0.9, easeInOutSine),
        ground().scale.x(1, 0.9, easeInOutSine),
        ground().opacity(0.5, 0.9, easeInOutSine),
      );
      yield* waitFor(0.3);
      break;
    }
    case 'idle': {
      // Seamless loop: starts and ends at the rest state with subtle glow.
      atRest();
      glow().opacity(0.22);
      glow().shadowBlur(14);
      yield* all(
        chain(
          all(
            emblem().position.y(-7, 1.4, easeInOutSine),
            ground().scale.x(0.92, 1.4, easeInOutSine),
            ground().opacity(0.4, 1.4, easeInOutSine),
          ),
          all(
            emblem().position.y(0, 1.4, easeInOutSine),
            ground().scale.x(1, 1.4, easeInOutSine),
            ground().opacity(0.5, 1.4, easeInOutSine),
          ),
        ),
        chain(
          all(glow().opacity(0.32, 1.4, easeInOutSine), glow().shadowBlur(20, 1.4, easeInOutSine)),
          all(glow().opacity(0.22, 1.4, easeInOutSine), glow().shadowBlur(14, 1.4, easeInOutSine)),
        ),
      );
      break;
    }
    case 'pulse': {
      // Seamless glow-breathing loop, no movement.
      atRest();
      glow().opacity(0.18);
      glow().shadowBlur(10);
      yield* chain(
        all(glow().opacity(0.7, 1.0, easeInOutSine), glow().shadowBlur(40, 1.0, easeInOutSine)),
        all(glow().opacity(0.18, 1.0, easeInOutSine), glow().shadowBlur(10, 1.0, easeInOutSine)),
      );
      break;
    }
    case 'glint': {
      atRest();
      yield* waitFor(0.15);
      yield* glintSweep();
      yield* waitFor(0.15);
      break;
    }
    default:
      throw new Error(`presetScene: unknown preset "${preset}"`);
  }
});
