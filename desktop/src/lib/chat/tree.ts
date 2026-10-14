// Conversation branching: messages form a tree via parent_id.
import type { Message } from '../api/types';

export function childrenMap(msgs: Message[]): Map<string | null, Message[]> {
  const m = new Map<string | null, Message[]>();
  for (const x of msgs) {
    const k = x.parent_id ?? null;
    if (!m.has(k)) m.set(k, []);
    m.get(k)!.push(x);
  }
  for (const list of m.values()) list.sort((a, b) => a.created_at - b.created_at);
  return m;
}

export function pathTo(msgs: Message[], leafId: string | null): Message[] {
  const byId = new Map(msgs.map((m) => [m.id, m]));
  const out: Message[] = [];
  let cur = leafId ? byId.get(leafId) : undefined;
  if (!cur && msgs.length) {
    // Fallback: follow latest children from the root.
    return descend(msgs, null);
  }
  while (cur) {
    out.push(cur);
    cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
  }
  return out.reverse();
}

/** Follows the most recent child at every level starting below `fromId`. */
export function descend(msgs: Message[], fromId: string | null): Message[] {
  const kids = childrenMap(msgs);
  const out: Message[] = [];
  let level = kids.get(fromId) ?? [];
  while (level.length) {
    const last = level[level.length - 1];
    out.push(last);
    level = kids.get(last.id) ?? [];
  }
  return out;
}

export function deepestLeaf(msgs: Message[], fromId: string): string {
  const below = descend(msgs, fromId);
  return below.length ? below[below.length - 1].id : fromId;
}

export function siblings(msgs: Message[], m: Message): Message[] {
  return msgs.filter((x) => x.parent_id === m.parent_id && x.role === m.role).sort((a, b) => a.created_at - b.created_at);
}
