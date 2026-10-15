<script lang="ts">
  import { persistPrefs, prefs } from '../stores/prefs.svelte';
  /** Draggable divider that resizes a neighbouring pane; size persists per id. */
  let { id, size = $bindable(), min = 200, max = 700, side = 'left' }: { id: string; size: number; min?: number; max?: number; side?: 'left' | 'right' } = $props();

  if (prefs.panelSizes[id]) size = prefs.panelSizes[id];

  let dragging = $state(false);
  function down(e: PointerEvent) {
    dragging = true;
    const startX = e.clientX;
    const start = size;
    const move = (ev: PointerEvent) => {
      const dx = ev.clientX - startX;
      size = Math.round(Math.min(max, Math.max(min, side === 'left' ? start + dx : start - dx)));
    };
    const up = () => {
      dragging = false;
      prefs.panelSizes[id] = size;
      persistPrefs();
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }
</script>

<div class="split" class:dragging role="separator" aria-orientation="vertical" onpointerdown={down} ondblclick={() => { delete prefs.panelSizes[id]; persistPrefs(); }}></div>

<style>
  .split { width: 7px; margin: 0 -3px; cursor: col-resize; position: relative; z-index: 5; flex-shrink: 0; }
  .split::after {
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    left: 3px;
    width: 1px;
    background: var(--line-1);
    transition: background var(--t-1), box-shadow var(--t-1);
  }
  .split:hover::after, .dragging::after { background: var(--accent-hi); box-shadow: 0 0 10px rgba(var(--accent-rgb), 0.6); }
</style>
