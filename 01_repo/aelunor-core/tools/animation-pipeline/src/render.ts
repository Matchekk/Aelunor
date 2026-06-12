/// <reference types="vite/client" />
/**
 * Browser-side entry for headless rendering. Motion Canvas has no official
 * CLI renderer yet (motion-canvas/motion-canvas#1218), so this page drives
 * the Renderer directly. The image-sequence exporter streams frames over the
 * Vite HMR channel and the Motion Canvas vite plugin writes them to ./output.
 *
 * scripts/render-headless.mjs loads this page in a headless browser and waits
 * for window.__renderDone / window.__renderError.
 */
import {Renderer} from '@motion-canvas/core';

declare global {
  interface Window {
    __renderDone?: boolean;
    __renderError?: string;
  }
}

async function main(): Promise<void> {
  // ?project=<name> selects which project to render (default: the chronicle);
  // ?vars=<json> feeds Motion Canvas project variables (used by presetScene).
  const params = new URLSearchParams(location.search);
  const which = params.get('project') ?? 'project';
  const project =
    which === 'logoProject'
      ? (await import('./logoProject?project')).default
      : which === 'presetProject'
        ? (await import('./presetProject?project')).default
        : (await import('./project?project')).default;
  const vars = params.get('vars');
  if (vars) {
    project.variables = JSON.parse(vars);
  }
  const renderer = new Renderer(project);
  const settings = project.meta.getFullRenderingSettings();
  await renderer.render({...settings, name: project.name});
  window.__renderDone = true;
}

main().catch(error => {
  window.__renderError = String(error instanceof Error ? error.stack : error);
});
