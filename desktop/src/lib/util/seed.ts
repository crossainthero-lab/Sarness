// The server's AI gateway validates seeds as signed 32-bit integers.
export const SEED_MAX = 2 ** 31 - 1;

export function randomSeed(rand: () => number = Math.random): number {
  return Math.floor(rand() * (SEED_MAX + 1));
}

/** User-typed seeds: keep in-range values, map anything else into range. -1 stays "random". */
export function safeSeed(value: number): number {
  if (!Number.isFinite(value) || value < 0) return -1;
  return Math.floor(value) % (SEED_MAX + 1);
}

/** Seed sent for Generate (image and video): random when requested, else the typed seed made safe. */
export function seedFor(randomize: boolean, typed: number): number {
  return randomize ? randomSeed() : safeSeed(typed) < 0 ? randomSeed() : safeSeed(typed);
}
