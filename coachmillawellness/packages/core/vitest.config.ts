import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      exclude: ['src/index.ts', 'src/types.ts', 'src/**/__tests__/**'],
      // Gate G1: 100% branch coverage on the scoring, checklist and coherence
      // maths. These are the rules of her practice — an untested branch here is
      // a session graded wrongly, so the threshold is not negotiable.
      thresholds: {
        'src/scoring.ts': { branches: 100, functions: 100, lines: 100, statements: 100 },
        'src/checklist.ts': { branches: 100, functions: 100, lines: 100, statements: 100 },
        'src/coherence.ts': { branches: 100, functions: 100, lines: 100, statements: 100 },
        'src/wheel.ts': { branches: 100, functions: 100, lines: 100, statements: 100 },
      },
    },
  },
});
