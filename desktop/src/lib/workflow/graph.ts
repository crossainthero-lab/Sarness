// Pure helpers converting between the Sarness workflow format and Svelte Flow
// nodes/edges, plus client-side connection validation (mirrors the engine).
import type { NodeLibrary, NodeSpec, Workflow, WfEdge, WfNode } from '../api/types';

export interface FlowNode {
  id: string;
  type: 'sarness' | 'reroute' | 'group';
  position: { x: number; y: number };
  data: { nodeType?: string; params?: Record<string, unknown>; label?: string; color?: string };
  parentId?: string;
  style?: string;
  width?: number;
  height?: number;
  selected?: boolean;
  zIndex?: number;
  dragHandle?: string;
  [k: string]: unknown;
}

export interface FlowEdge {
  id: string;
  source: string;
  sourceHandle: string;
  target: string;
  targetHandle: string;
  style?: string;
  data?: { type: string };
  selected?: boolean;
  class?: string;
  animated?: boolean;
  [k: string]: unknown;
}

export const ANY = 'ANY';

export function compatible(src: string, dst: string): boolean {
  if (src === dst || src === ANY || dst === ANY) return true;
  return src === 'INT' && dst === 'FLOAT';
}

export function specMap(lib: NodeLibrary | null): Map<string, NodeSpec> {
  return new Map((lib?.nodes ?? []).map((n) => [n.type, n]));
}

export function uid(prefix = 'n') {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}${Date.now().toString(36).slice(-3)}`;
}

/** Input sockets of a node, including params promoted to sockets. */
export function inputSockets(spec: NodeSpec) {
  return [
    ...spec.inputs.map((s) => ({ ...s, param: false })),
    ...spec.params.filter((p) => p.socket).map((p) => ({ name: p.name, type: p.socket_type ?? 'STRING', label: p.label, optional: true, param: true })),
  ];
}

export function inputType(spec: NodeSpec, name: string): string | null {
  if (spec.passthrough) return ANY;
  return inputSockets(spec).find((s) => s.name === name)?.type ?? null;
}

/** Output type, following reroute (passthrough) nodes upstream. */
export function outputType(nodeId: string, handle: string, nodes: FlowNode[], edges: FlowEdge[], specs: Map<string, NodeSpec>, seen = new Set<string>()): string | null {
  const n = nodes.find((x) => x.id === nodeId);
  if (!n) return null;
  const spec = specs.get(n.data.nodeType ?? '');
  if (!spec) return null;
  if (spec.passthrough) {
    if (seen.has(nodeId)) return ANY;
    seen.add(nodeId);
    const inc = edges.find((e) => e.target === nodeId);
    return inc ? outputType(inc.source, inc.sourceHandle, nodes, edges, specs, seen) : ANY;
  }
  return spec.outputs.find((o) => o.name === handle)?.type ?? null;
}

export function wouldCycle(source: string, target: string, edges: FlowEdge[]): boolean {
  if (source === target) return true;
  const stack = [target];
  const seen = new Set<string>();
  while (stack.length) {
    const cur = stack.pop()!;
    if (cur === source) return true;
    if (seen.has(cur)) continue;
    seen.add(cur);
    for (const e of edges) if (e.source === cur) stack.push(e.target);
  }
  return false;
}

export function connectionError(
  c: { source: string; sourceHandle?: string | null; target: string; targetHandle?: string | null },
  nodes: FlowNode[], edges: FlowEdge[], specs: Map<string, NodeSpec>,
): string | null {
  const tn = nodes.find((n) => n.id === c.target);
  const tspec = specs.get(tn?.data.nodeType ?? '');
  if (!tspec || !c.targetHandle || !c.sourceHandle) return 'invalid connection';
  const dst = inputType(tspec, c.targetHandle);
  const src = outputType(c.source, c.sourceHandle, nodes, edges, specs);
  if (!dst || !src) return 'unknown socket';
  if (!compatible(src, dst)) return `${src} cannot connect to ${dst}`;
  if (wouldCycle(c.source, c.target, edges)) return 'this would create a cycle';
  return null;
}

export function edgeColor(type: string, lib: NodeLibrary | null): string {
  return lib?.socket_types.find((s) => s.type === type)?.color ?? '#a1a1aa';
}

// ------------------------------------------------------------------ convert
export function toFlow(wf: Workflow, specs: Map<string, NodeSpec>, lib: NodeLibrary | null): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const nodes: FlowNode[] = [];
  const groupOf = new Map<string, string>();
  for (const g of wf.groups ?? []) {
    if (!g.rect) continue;
    nodes.push({
      id: g.id, type: 'group', position: { x: g.rect.x, y: g.rect.y },
      data: { label: g.label, color: g.color },
      width: g.rect.width, height: g.rect.height,
      style: `width:${g.rect.width}px;height:${g.rect.height}px;`, zIndex: -1,
    });
    for (const nid of g.nodes) groupOf.set(nid, g.id);
  }
  for (const n of wf.nodes) {
    const spec = specs.get(n.type);
    const gid = groupOf.get(n.id);
    const g = gid ? wf.groups.find((x) => x.id === gid) : null;
    const pos = g?.rect ? { x: n.position.x - g.rect.x, y: n.position.y - g.rect.y } : { ...n.position };
    nodes.push({
      id: n.id,
      type: spec?.passthrough ? 'reroute' : 'sarness',
      position: pos,
      data: { nodeType: n.type, params: { ...defaultsFor(spec), ...(n.params ?? {}) }, label: n.label, color: n.color },
      ...(gid ? { parentId: gid } : {}),
    });
  }
  const edges: FlowEdge[] = wf.edges.map((e) => {
    const t = outputTypeFromWf(wf, e, specs);
    return {
      id: e.id, source: e.source, sourceHandle: e.source_output, target: e.target, targetHandle: e.target_input,
      data: { type: t }, style: `stroke:${edgeColor(t, lib)};`,
    };
  });
  return { nodes, edges };
}

function outputTypeFromWf(wf: Workflow, e: WfEdge, specs: Map<string, NodeSpec>): string {
  const n = wf.nodes.find((x) => x.id === e.source);
  const spec = specs.get(n?.type ?? '');
  if (!spec) return ANY;
  if (spec.passthrough) {
    const inc = wf.edges.find((x) => x.target === e.source);
    return inc ? outputTypeFromWf(wf, inc, specs) : ANY;
  }
  return spec.outputs.find((o) => o.name === e.source_output)?.type ?? ANY;
}

export function defaultsFor(spec: NodeSpec | undefined): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const p of spec?.params ?? []) out[p.name] = p.default;
  return out;
}

export function fromFlow(nodes: FlowNode[], edges: FlowEdge[], base: Partial<Workflow>): Workflow {
  const groups = nodes.filter((n) => n.type === 'group');
  const abs = (n: FlowNode) => {
    if (!n.parentId) return n.position;
    const p = groups.find((g) => g.id === n.parentId);
    return p ? { x: p.position.x + n.position.x, y: p.position.y + n.position.y } : n.position;
  };
  const wfNodes: WfNode[] = nodes
    .filter((n) => n.type !== 'group')
    .map((n) => ({
      id: n.id,
      type: n.data.nodeType!,
      params: { ...(n.data.params ?? {}) },
      position: { x: Math.round(abs(n).x), y: Math.round(abs(n).y) },
      ...(n.data.label ? { label: n.data.label } : {}),
    }));
  return {
    format: 'sarness.workflow',
    version: 1,
    name: base.name ?? 'Untitled workflow',
    kind: base.kind ?? 'image',
    nodes: wfNodes,
    edges: edges.map((e) => ({ id: e.id, source: e.source, source_output: e.sourceHandle, target: e.target, target_input: e.targetHandle })),
    groups: groups.map((g) => ({
      id: g.id,
      label: g.data.label ?? 'Group',
      color: g.data.color,
      nodes: nodes.filter((n) => n.parentId === g.id).map((n) => n.id),
      rect: { x: Math.round(g.position.x), y: Math.round(g.position.y), width: Math.round(g.width ?? 400), height: Math.round(g.height ?? 300) },
    })),
    ...(base.ui ? { ui: base.ui } : {}),
  };
}

/** Clone a selection with fresh ids (for copy/paste/duplicate). */
export function cloneSelection(nodes: FlowNode[], edges: FlowEdge[], offset = 40): { nodes: FlowNode[]; edges: FlowEdge[] } {
  const map = new Map<string, string>();
  for (const n of nodes) map.set(n.id, uid(n.type === 'group' ? 'g' : 'n'));
  const outNodes = nodes.map((n) => ({
    ...structuredClone(n),
    id: map.get(n.id)!,
    parentId: n.parentId && map.has(n.parentId) ? map.get(n.parentId) : undefined,
    position: n.parentId && map.has(n.parentId) ? n.position : { x: n.position.x + offset, y: n.position.y + offset },
    selected: true,
  }));
  const outEdges = edges
    .filter((e) => map.has(e.source) && map.has(e.target))
    .map((e) => ({ ...structuredClone(e), id: uid('e'), source: map.get(e.source)!, target: map.get(e.target)!, selected: false }));
  return { nodes: outNodes, edges: outEdges };
}
