export const ASPECTS = [
  { value: '1:1', w: 1, h: 1 },
  { value: '4:3', w: 4, h: 3 },
  { value: '3:4', w: 3, h: 4 },
  { value: '3:2', w: 3, h: 2 },
  { value: '2:3', w: 2, h: 3 },
  { value: '16:9', w: 16, h: 9 },
  { value: '9:16', w: 9, h: 16 },
  { value: '21:9', w: 21, h: 9 },
];

/** Picks dimensions with the requested aspect and (approximately) the given pixel area. */
export function dimsFor(aspect: string, area: number, multiple = 64, minSide = 256, maxSide = 2048): [number, number] {
  const a = ASPECTS.find((x) => x.value === aspect) ?? ASPECTS[0];
  let w = Math.sqrt((area * a.w) / a.h);
  let h = area / w;
  const scale = Math.min(1, maxSide / Math.max(w, h));
  w *= scale;
  h *= scale;
  const snap = (v: number) => Math.min(maxSide, Math.max(minSide, Math.round(v / multiple) * multiple));
  return [snap(w), snap(h)];
}
