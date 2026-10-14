<script lang="ts">
  import { Handle, Position, type NodeProps } from '@xyflow/svelte';
  let { selected }: NodeProps = $props();
</script>

<div class="rr" class:selected title="Reroute">
  <Handle type="target" position={Position.Left} id="in" class="rh" />
  <Handle type="source" position={Position.Right} id="out" class="rh" />
</div>

<style>
  .rr { width: 16px; height: 16px; border-radius: 50%; background: var(--bg-5); border: 2px solid var(--text-2); }
  .selected { border-color: var(--lavender); box-shadow: 0 0 10px rgba(167, 139, 250, 0.6); }
  .rr :global(.rh) { width: 8px !important; height: 8px !important; opacity: 0; border: 0 !important; }
  .rr :global(.rh[data-handlepos='left']) { left: 0 !important; }
  .rr :global(.rh[data-handlepos='right']) { right: 0 !important; }
</style>
