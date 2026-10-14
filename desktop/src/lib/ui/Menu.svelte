<script lang="ts" module>
  import type { Component } from 'svelte';
  export interface MenuItem {
    label?: string;
    icon?: Component;
    run?: () => void;
    danger?: boolean;
    disabled?: boolean;
    separator?: boolean;
    hint?: string;
  }
</script>

<script lang="ts">
  import { tick } from 'svelte';
  let { items = $bindable([]), x = $bindable(0), y = $bindable(0), open = $bindable(false) }: { items: MenuItem[]; x: number; y: number; open: boolean } = $props();
  let el: HTMLDivElement | undefined = $state();
  let pos = $state({ x: 0, y: 0 });

  $effect(() => {
    if (open) {
      pos = { x, y };
      tick().then(() => {
        if (!el) return;
        const r = el.getBoundingClientRect();
        pos = { x: Math.min(x, window.innerWidth - r.width - 8), y: Math.min(y, window.innerHeight - r.height - 8) };
      });
    }
  });
</script>

<svelte:window onmousedown={(e) => open && el && !el.contains(e.target as Node) && (open = false)} onkeydown={(e) => e.key === 'Escape' && (open = false)} onblur={() => (open = false)} />

{#if open}
  <div bind:this={el} class="menu glass" role="menu" style="left:{pos.x}px;top:{pos.y}px">
    {#each items as it, i (i)}
      {#if it.separator}
        <div class="sep"></div>
      {:else}
        <button type="button" role="menuitem" class:danger={it.danger} disabled={it.disabled} onclick={() => { open = false; it.run?.(); }}>
          {#if it.icon}<it.icon />{:else}<span class="ph"></span>{/if}
          <span class="lbl">{it.label}</span>
          {#if it.hint}<span class="hint">{it.hint}</span>{/if}
        </button>
      {/if}
    {/each}
  </div>
{/if}

<style>
  .menu {
    position: fixed;
    z-index: 9500;
    min-width: 190px;
    padding: 5px;
    border-radius: var(--r-lg);
    background: var(--glass-strong);
    box-shadow: var(--shadow-3);
    animation: pop-in var(--t-1) var(--ease-out);
  }
  button {
    display: flex;
    align-items: center;
    gap: 9px;
    width: 100%;
    padding: 7px 9px;
    border: 0;
    border-radius: var(--r-sm);
    background: none;
    color: var(--text-1);
    font-size: var(--fs-md);
    text-align: left;
    cursor: pointer;
  }
  button:hover:not(:disabled) { background: rgba(255, 255, 255, 0.07); color: var(--text-0); }
  button:disabled { opacity: 0.4; cursor: default; }
  button :global(svg), .ph { width: 15px; height: 15px; color: var(--text-2); flex-shrink: 0; }
  .danger { color: var(--err); }
  .danger:hover:not(:disabled) { background: var(--err-bg) !important; color: var(--err) !important; }
  .danger :global(svg) { color: var(--err); }
  .lbl { flex: 1; }
  .hint { font-size: var(--fs-xs); color: var(--text-3); }
  .sep { height: 1px; margin: 4px 6px; background: var(--line-1); }
</style>
