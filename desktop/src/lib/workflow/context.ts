import { getContext, setContext } from 'svelte';
import type { NodeLibrary, NodeSpec, NodeState } from '../api/types';

export interface EditorCtx {
  readonly specs: Map<string, NodeSpec>;
  readonly lib: NodeLibrary | null;
  readonly kind: 'image' | 'video';
  state(nodeId: string): NodeState | null;
  progress(nodeId: string): { value: number; text: string | null } | null;
  preview(nodeId: string): string | null;
  output(nodeId: string): string | null;
  issue(nodeId: string): string | null;
  connected(nodeId: string, handle: string): boolean;
  setParam(nodeId: string, name: string, value: unknown): void;
  rename(nodeId: string): void;
  socketColor(type: string): string;
}

const KEY = Symbol('wf-editor');
export const setEditor = (c: EditorCtx) => setContext(KEY, c);
export const editor = () => getContext<EditorCtx>(KEY);
