import { describe, expect, it } from 'vitest';
import type { Message } from '../api/types';
import { deepestLeaf, pathTo, siblings } from './tree';

const m = (id: string, parent: string | null, role: 'user' | 'assistant', t: number): Message =>
  ({ id, parent_id: parent, role, created_at: t, content: id, attachments: [], conversation_id: 'c', model_ref: null, stats: null, status: 'complete' });

const msgs = [m('u1', null, 'user', 1), m('a1', 'u1', 'assistant', 2), m('a1b', 'u1', 'assistant', 3), m('u2', 'a1', 'user', 4), m('a2', 'u2', 'assistant', 5)];

describe('conversation tree', () => {
  it('builds the active path and switches branches', () => {
    expect(pathTo(msgs, 'a2').map((x) => x.id)).toEqual(['u1', 'a1', 'u2', 'a2']);
    expect(pathTo(msgs, 'a1b').map((x) => x.id)).toEqual(['u1', 'a1b']);
    expect(siblings(msgs, msgs[1]).map((x) => x.id)).toEqual(['a1', 'a1b']);
    expect(deepestLeaf(msgs, 'a1')).toBe('a2');
    expect(deepestLeaf(msgs, 'a1b')).toBe('a1b');
  });
});
