import { describe, expect, it } from 'vitest';
import { randomSeed, safeSeed, seedFor, SEED_MAX } from './seed';

describe('seeds', () => {
  it('random seeds stay within signed int32, including the extremes', () => {
    expect(randomSeed(() => 0)).toBe(0);
    expect(randomSeed(() => 0.9999999999999999)).toBe(SEED_MAX);
    for (let i = 0; i < 5000; i++) {
      const s = randomSeed();
      expect(Number.isInteger(s) && s >= 0 && s <= SEED_MAX).toBe(true);
    }
  });
  it('typed seeds are kept or clamped', () => {
    expect(safeSeed(42)).toBe(42);
    expect(safeSeed(SEED_MAX)).toBe(SEED_MAX);
    expect(safeSeed(2 ** 32 - 1)).toBeLessThanOrEqual(SEED_MAX);
    expect(safeSeed(-5)).toBe(-1);
    expect(safeSeed(NaN)).toBe(-1);
  });
  it('Generate, Regenerate, Vary and video all draw from the safe range', () => {
    expect(seedFor(false, 123)).toBe(123);
    for (let i = 0; i < 2000; i++) {
      for (const s of [seedFor(true, 0), seedFor(false, 2 ** 40), seedFor(false, -9), randomSeed()]) {
        expect(s).toBeGreaterThanOrEqual(0);
        expect(s).toBeLessThanOrEqual(SEED_MAX);
      }
    }
  });
});
