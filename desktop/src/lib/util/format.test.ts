import { describe, expect, it } from 'vitest';
import { bytes, duration, mib, snap } from './format';
import { dimsFor } from '../studio/aspect';

describe('format', () => {
  it('formats bytes and durations', () => {
    expect(bytes(2_500_000_000)).toBe('2.5 GB');
    expect(mib(12288)).toBe('12.0 GB');
    expect(duration(0.25)).toBe('250 ms');
    expect(duration(95)).toBe('1m 35s');
    expect(snap(1001, 64)).toBe(1024);
  });
  it('computes aspect dimensions on a grid', () => {
    expect(dimsFor('1:1', 1024 * 1024)).toEqual([1024, 1024]);
    const [w, h] = dimsFor('16:9', 1024 * 1024);
    expect(w % 64).toBe(0);
    expect(h % 64).toBe(0);
    expect(w / h).toBeCloseTo(16 / 9, 0);
    const [w2, h2] = dimsFor('21:9', 1024 * 1024, 64, 256, 1536);
    expect(Math.max(w2, h2)).toBeLessThanOrEqual(1536);
  });
});
