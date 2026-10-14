<script lang="ts">
  import { NodeResizer, type NodeProps } from '@xyflow/svelte';
  import { editor } from './context';
  let { id, data, selected }: NodeProps = $props();
  const ed = editor();
</script>

<NodeResizer minWidth={200} minHeight={120} isVisible={selected} lineClass="grp-line" handleClass="grp-handle" />
<div class="grp" class:selected style="--gc:{(data.color as string) ?? '#8b5cf6'}">
  <div class="gl" ondblclick={() => ed.rename(id)} role="presentation">{(data.label as string) ?? 'Group'}</div>
</div>

<style>
  .grp {
    width: 100%;
    height: 100%;
    border-radius: 16px;
    background: color-mix(in srgb, var(--gc) 6%, transparent);
    border: 1px dashed color-mix(in srgb, var(--gc) 40%, transparent);
  }
  .selected { border-style: solid; background: color-mix(in srgb, var(--gc) 9%, transparent); }
  .gl { padding: 8px 12px; font-weight: 650; font-size: 13px; color: color-mix(in srgb, var(--gc) 70%, white); letter-spacing: -0.01em; }
  :global(.grp-line) { border-color: var(--accent-hi) !important; }
  :global(.grp-handle) { background: var(--accent-hi) !important; border: 0 !important; width: 8px !important; height: 8px !important; border-radius: 2px !important; }
</style>
