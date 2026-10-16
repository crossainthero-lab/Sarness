<script lang="ts" generics="T extends string | number">
  import type { Component } from 'svelte';
  interface Item { value: T; label?: string; icon?: Component; title?: string; disabled?: boolean }
  let { value = $bindable(), items, size = 'md', onchange, full = false }: { value: T; items: Item[]; size?: 'sm' | 'md'; onchange?: (v: T) => void; full?: boolean } = $props();
</script>

<div class="seg {size}" class:full role="radiogroup">
  {#each items as it (it.value)}
    <button type="button" role="radio" aria-checked={value === it.value} class:on={value === it.value} disabled={it.disabled}
      title={it.title ?? it.label} onclick={() => { value = it.value; onchange?.(it.value); }}>
      {#if it.icon}<it.icon />{/if}
      {#if it.label}<span>{it.label}</span>{/if}
    </button>
  {/each}
</div>

<style>
  .seg {
    display: inline-flex;
    padding: 3px;
    gap: 2px;
    border-radius: var(--r-md);
    background: var(--bg-1);
    border: 1px solid var(--line-1);
  }
  .full { display: flex; width: 100%; }
  .full button { flex: 1; }
  button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 26px;
    padding: 0 10px;
    border: 0;
    border-radius: var(--r-sm);
    background: transparent;
    color: var(--text-2);
    font-size: var(--fs-sm);
    font-weight: 550;
    cursor: pointer;
    white-space: nowrap;
    transition: background var(--t-1) var(--ease), color var(--t-1) var(--ease);
  }
  .sm button { height: 22px; padding: 0 8px; font-size: var(--fs-xs); }
  button :global(svg) { width: 14px; height: 14px; }
  button:hover:not(.on):not(:disabled) { color: var(--text-0); background: rgba(var(--fg-rgb), 0.04); }
  button.on { background: var(--bg-5); color: var(--text-0); box-shadow: 0 1px 0 rgba(var(--fg-rgb), 0.06) inset, 0 1px 3px rgba(0, 0, 0, 0.4); }
  button:disabled { opacity: 0.35; cursor: default; }
</style>
