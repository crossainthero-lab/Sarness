<script lang="ts">
  import type { Component, Snippet } from 'svelte';
  let { icon, title, body = '', children, compact = false }: { icon?: Component; title: string; body?: string; children?: Snippet; compact?: boolean } = $props();
</script>

<div class="empty" class:compact>
  {#if icon}{@const I = icon}<div class="ic"><I /></div>{/if}
  <h3>{title}</h3>
  {#if body}<p>{body}</p>{/if}
  {#if children}<div class="actions">{@render children()}</div>{/if}
</div>

<style>
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 8px;
    padding: 48px 24px;
    color: var(--text-2);
    animation: fade-in var(--t-3) var(--ease);
  }
  .compact { padding: 24px 16px; }
  .ic {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    margin-bottom: 6px;
    border-radius: 14px;
    background: linear-gradient(180deg, var(--bg-4), var(--bg-3));
    border: 1px solid var(--line-1);
    color: var(--lavender);
    box-shadow: var(--shadow-2);
  }
  .ic :global(svg) { width: 22px; height: 22px; }
  h3 { font-size: var(--fs-lg); color: var(--text-0); }
  p { max-width: 380px; font-size: var(--fs-md); line-height: 1.55; }
  .actions { display: flex; gap: 8px; margin-top: 10px; }
</style>
