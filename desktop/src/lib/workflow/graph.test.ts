import { describe, expect, it } from 'vitest';
import type { NodeLibrary, Workflow } from '../api/types';
import { cloneSelection, compatible, connectionError, fromFlow, specMap, toFlow, wouldCycle } from './graph';

const lib: NodeLibrary = {
  format: 'sarness.workflow', version: 1, categories: [],
  socket_types: [{ type: 'IMAGE', color: '#60a5fa' }, { type: 'LATENT', color: '#fb923c' }],
  nodes: [
    { type: 'image.load', title: 'Load', category: 'Image', description: '', inputs: [], outputs: [{ name: 'image', type: 'IMAGE', label: 'Image', optional: false }], params: [{ name: 'file', kind: 'file', default: '', label: 'File' }], output_node: false, gpu: false, passthrough: false, tags: [] },
    { type: 'image.blur', title: 'Blur', category: 'Transform', description: '', inputs: [{ name: 'image', type: 'IMAGE', label: 'Image', optional: false }], outputs: [{ name: 'image', type: 'IMAGE', label: 'Image', optional: false }], params: [{ name: 'radius', kind: 'float', default: 2, label: 'Radius', socket: true, socket_type: 'FLOAT' }], output_node: false, gpu: false, passthrough: false, tags: [] },
    { type: 'vae.decode', title: 'Decode', category: 'VAE', description: '', inputs: [{ name: 'latent', type: 'LATENT', label: 'Latent', optional: false }], outputs: [{ name: 'image', type: 'IMAGE', label: 'Image', optional: false }], params: [], output_node: false, gpu: true, passthrough: false, tags: [] },
    { type: 'util.reroute', title: 'Reroute', category: 'Utility', description: '', inputs: [{ name: 'in', type: 'ANY', label: 'In', optional: false }], outputs: [{ name: 'out', type: 'ANY', label: 'Out', optional: false }], params: [], output_node: false, gpu: false, passthrough: true, tags: [] },
  ],
};
const specs = specMap(lib);

const wf: Workflow = {
  format: 'sarness.workflow', version: 1, name: 't', kind: 'image',
  nodes: [
    { id: 'a', type: 'image.load', params: { file: 'f1' }, position: { x: 0, y: 0 } },
    { id: 'r', type: 'util.reroute', params: {}, position: { x: 200, y: 0 } },
    { id: 'b', type: 'image.blur', params: {}, position: { x: 400, y: 0 } },
    { id: 'd', type: 'vae.decode', params: {}, position: { x: 400, y: 200 } },
  ],
  edges: [
    { id: 'e1', source: 'a', source_output: 'image', target: 'r', target_input: 'in' },
    { id: 'e2', source: 'r', source_output: 'out', target: 'b', target_input: 'image' },
  ],
  groups: [{ id: 'g', label: 'Inputs', nodes: ['a'], rect: { x: -20, y: -40, width: 300, height: 200 } }],
};

describe('workflow graph', () => {
  it('round-trips through flow nodes including groups', () => {
    const { nodes, edges } = toFlow(wf, specs, lib);
    const a = nodes.find((n) => n.id === 'a')!;
    expect(a.parentId).toBe('g');
    expect(a.position).toEqual({ x: 20, y: 40 });
    expect(nodes.find((n) => n.id === 'r')!.type).toBe('reroute');
    expect(nodes.find((n) => n.id === 'b')!.data.params!.radius).toBe(2); // defaults filled
    const back = fromFlow(nodes, edges, { name: 't', kind: 'image' });
    expect(back.nodes.find((n) => n.id === 'a')!.position).toEqual({ x: 0, y: 0 });
    expect(back.edges).toEqual(wf.edges);
    expect(back.groups[0].nodes).toEqual(['a']);
  });

  it('validates types through reroutes and refuses cycles', () => {
    const { nodes, edges } = toFlow(wf, specs, lib);
    // IMAGE (via reroute) into LATENT input is rejected.
    expect(connectionError({ source: 'r', sourceHandle: 'out', target: 'd', targetHandle: 'latent' }, nodes, edges, specs)).toMatch(/IMAGE cannot connect to LATENT/);
    // Cycle b -> a is rejected (a feeds b).
    expect(wouldCycle('b', 'a', edges)).toBe(true);
    expect(compatible('INT', 'FLOAT')).toBe(true);
    expect(compatible('FLOAT', 'INT')).toBe(false);
  });

  it('clones selections with fresh ids and internal edges only', () => {
    const { nodes, edges } = toFlow(wf, specs, lib);
    const sel = nodes.filter((n) => n.id === 'r' || n.id === 'b');
    const c = cloneSelection(sel, edges);
    expect(c.nodes.map((n) => n.id)).not.toContain('r');
    expect(c.edges).toHaveLength(1);
    expect(c.edges[0].source).toBe(c.nodes[0].id);
  });
});
