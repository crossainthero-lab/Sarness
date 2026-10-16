import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamChat } from './client';

const sse = (...events: object[]) => {
  const enc = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(c) {
      for (const e of events) c.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
      c.close();
    },
  });
};
const mockFetch = (body: ReadableStream<Uint8Array>) =>
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, body, json: async () => ({}) })));

afterEach(() => vi.unstubAllGlobals());

describe('streamChat interruption handling', () => {
  it('resolves when the stream ends with a done event', async () => {
    mockFetch(sse({ type: 'delta', content: 'hi' }, { type: 'done', message: { id: 'm' } }));
    const seen: string[] = [];
    await expect(streamChat('/x', {}, (e) => seen.push(e.type))).resolves.toBeUndefined();
    expect(seen).toEqual(['delta', 'done']);
  });
  it('rejects when the connection closes before a terminal event', async () => {
    mockFetch(sse({ type: 'delta', content: 'partial' }));
    await expect(streamChat('/x', {}, () => {})).rejects.toMatchObject({ status: 0 });
  });
  it('treats a server error event as terminal, not as an interruption', async () => {
    mockFetch(sse({ type: 'error', message: 'boom' }));
    await expect(streamChat('/x', {}, () => {})).resolves.toBeUndefined();
  });
  it('does not report an interruption when the user aborts', async () => {
    const ac = new AbortController();
    ac.abort();
    mockFetch(sse({ type: 'delta', content: 'x' }));
    await expect(streamChat('/x', {}, () => {}, ac.signal)).resolves.toBeUndefined();
  });
});
