import { describe, expect, it } from 'vitest';
import { extractBlocks, isTextFile, lineDiff, previousVersion } from './code';

const msg = (id: string, content: string) => ({ id, role: 'assistant', content });

describe('extractBlocks', () => {
  it('reads language and filename from the info string', () => {
    const b = extractBlocks([msg('m1', 'Here:\n```ts src/a.ts\nconst a = 1;\n```\nand\n```python\nprint(1)\n```')]);
    expect(b).toHaveLength(2);
    expect(b[0]).toMatchObject({ lang: 'ts', filename: 'src/a.ts', code: 'const a = 1;' });
    expect(b[1]).toMatchObject({ lang: 'python', filename: null });
  });
  it('supports title= and leading file comments', () => {
    const b = extractBlocks([msg('m', '```js title="x/y.js"\n1\n```\n```py\n# file: tool.py\nx=1\n```')]);
    expect(b[0].filename).toBe('x/y.js');
    expect(b[1].filename).toBe('tool.py');
  });
  it('ignores user messages', () => {
    expect(extractBlocks([{ id: 'u', role: 'user', content: '```js\n1\n```' }])).toHaveLength(0);
  });
});

describe('lineDiff', () => {
  it('marks additions and deletions', () => {
    const d = lineDiff('a\nb\nc', 'a\nc\nd');
    expect(d.filter((l) => l.kind === 'del').map((l) => l.text)).toEqual(['b']);
    expect(d.filter((l) => l.kind === 'add').map((l) => l.text)).toEqual(['d']);
  });
});

describe('previousVersion', () => {
  it('finds the earlier block for the same file', () => {
    const b = extractBlocks([msg('1', '```ts a.ts\nx\n```'), msg('2', '```ts b.ts\ny\n```'), msg('3', '```ts a.ts\nz\n```')]);
    expect(previousVersion(b, 2)?.key).toBe('1:0');
    expect(previousVersion(b, 1)).toBeNull();
  });
});

describe('isTextFile', () => {
  it('accepts source and rejects binaries', () => {
    expect(isTextFile('src/main.rs')).toBe(true);
    expect(isTextFile('logo.png')).toBe(false);
  });
});
