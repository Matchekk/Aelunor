import {defineConfig} from 'vite';
import motionCanvasPlugin from '@motion-canvas/vite-plugin';

// The plugin ships as CJS; Node's ESM interop wraps it in another `default`.
const motionCanvas =
  typeof motionCanvasPlugin === 'function'
    ? motionCanvasPlugin
    : (motionCanvasPlugin as {default: typeof motionCanvasPlugin}).default;

export default defineConfig({
  plugins: [
    motionCanvas({
      project: ['./src/project.ts', './src/logoProject.ts', './src/presetProject.ts'],
      // Frames exported by the image-sequence exporter land here.
      output: './output',
    }),
  ],
  server: {
    // The scene imports the sprite sheet straight from ui/public so there is
    // a single source of truth — allow serving files from the package root.
    fs: {
      allow: ['../..'],
    },
  },
});
