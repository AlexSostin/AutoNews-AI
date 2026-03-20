/**
 * Global state for article generation progress.
 * Used by GenerationDrawer + any page that triggers generation.
 */
import { create } from 'zustand';

export type GenerationStep =
  | 'idle'
  | 'starting'
  | 'transcript'
  | 'facts'
  | 'writing'
  | 'factcheck'
  | 'review'
  | 'quality'
  | 'saving'
  | 'done'
  | 'error'
  | 'timeout';

export interface GenerationState {
  /** Is a generation currently in progress? */
  isRunning: boolean;
  /** The YouTube URL or article title being generated */
  label: string;
  /** Percentage 0–100 */
  progress: number;
  /** Current step key */
  step: GenerationStep;
  /** Article slug/id on completion — for "Edit Article" link */
  articleSlug: string | null;
  /** Error message on failure */
  errorMessage: string | null;
  /** Whether the drawer is minimized to the pill */
  minimized: boolean;

  // Actions
  startGeneration: (label: string) => void;
  updateProgress: (progress: number, step: GenerationStep) => void;
  finishGeneration: (articleSlug: string) => void;
  failGeneration: (message: string, timeout?: boolean) => void;
  dismiss: () => void;
  toggleMinimize: () => void;
}

export const useGenerationStore = create<GenerationState>((set) => ({
  isRunning: false,
  label: '',
  progress: 0,
  step: 'idle',
  articleSlug: null,
  errorMessage: null,
  minimized: false,

  startGeneration: (label) =>
    set({
      isRunning: true,
      label,
      progress: 5,
      step: 'starting',
      articleSlug: null,
      errorMessage: null,
      minimized: false,
    }),

  updateProgress: (progress, step) =>
    set({ progress, step }),

  finishGeneration: (articleSlug) =>
    set({
      isRunning: false,
      progress: 100,
      step: 'done',
      articleSlug,
      minimized: false,
    }),

  failGeneration: (message, timeout = false) =>
    set({
      isRunning: false,
      progress: 0,
      step: timeout ? 'timeout' : 'error',
      errorMessage: message,
      minimized: false,
    }),

  dismiss: () =>
    set({
      isRunning: false,
      label: '',
      progress: 0,
      step: 'idle',
      articleSlug: null,
      errorMessage: null,
      minimized: false,
    }),

  toggleMinimize: () => set((s) => ({ minimized: !s.minimized })),
}));

/** Map WebSocket / polling progress % to a step label */
export function percentToStep(pct: number): GenerationStep {
  if (pct < 10) return 'starting';
  if (pct < 25) return 'transcript';
  if (pct < 40) return 'facts';
  if (pct < 70) return 'writing';
  if (pct < 80) return 'factcheck';
  if (pct < 90) return 'review';
  if (pct < 98) return 'quality';
  if (pct < 100) return 'saving';
  return 'done';
}
