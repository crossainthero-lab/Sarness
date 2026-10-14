<script lang="ts">
  import { ChevronRight } from '@lucide/svelte';
  import type { Snippet } from 'svelte';
  import { slide } from 'svelte/transition';
  let { title, open = $bindable(false), children, aside }: { title: string; open?: boolean; children: Snippet; aside?: Snippet } = $props();
</script>

<section class="coll">
  <button type="button" class="head" class:open onclick={() => (open = !open)} aria-expanded={open}>
    <ChevronRight />
    <span>{title}</span>
    {#if aside}<span class="aside">{@render aside()}</span>{/if}
  </button>
  {#if open}
    <div class="body" transition:slide={{ duration: 200 }}>{@render children()}</div>
  {/if}
</section>

<style>
  .coll { border-top: 1px solid var(--line-0); }
  .head {
    display: flex;
    align-items: center;
    gap: 7px;
    width: 100%;
    padding: 11px 2px;
    border: 0;
    background: none;
    color: var(--text-1);
    font-weight: 600;
    font-size: var(--fs-sm);
    cursor: pointer;
  }
  .head:hover { color: var(--text-0); }
  .head :global(svg) { width: 14px; height: 14px; color: var(--text-3); transition: transform var(--t-2) var(--ease); }
  .head.open :global(svg) { transform: rotate(90deg); }
  .aside { margin-left: auto; font-weight: 500; color: var(--text-3); }
  .body { display: flex; flex-direction: column; gap: 14px; padding: 2px 2px 16px; }
</style>
