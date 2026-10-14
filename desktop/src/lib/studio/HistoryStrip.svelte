<script lang="ts">
  import { Play, Star } from '@lucide/svelte';
  import { mediaUrl } from '../api/transport';
  import type { History } from '../stores/history.svelte';

  let { history }: { history: History } = $props();
  let strip: HTMLDivElement | undefined = $state();

  $effect(() => {
    const i = history.state.index;
    strip?.querySelector<HTMLElement>(`[data-i="${i}"]`)?.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
  });

  function scroll(e: Event) {
    const el = e.currentTarget as HTMLDivElement;
    if (el.scrollLeft + el.clientWidth > el.scrollWidth - 200) history.more();
  }
  function wheel(e: WheelEvent) {
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      (e.currentTarget as HTMLDivElement).scrollLeft += e.deltaY;
      e.preventDefault();
    }
  }
</script>

<div class="strip" bind:this={strip} onscroll={scroll} onwheel={wheel}>
  {#each history.state.items as g, i (g.id)}
    <button class="thumb" class:active={i === history.state.index} data-i={i} onclick={() => (history.state.index = i)} title={g.prompt ?? ''}>
      <img src={mediaUrl(g.thumb_url)} alt="" loading="lazy" decoding="async" />
      {#if g.type === 'video'}<span class="badge"><Play /></span>{/if}
      {#if g.favorite}<span class="fav"><Star /></span>{/if}
    </button>
  {/each}
</div>

<style>
  .strip {
    display: flex;
    gap: 8px;
    padding: 10px 16px 12px;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-behavior: smooth;
    min-height: 88px;
  }
  .thumb {
    position: relative;
    flex: 0 0 auto;
    width: 68px;
    height: 68px;
    padding: 0;
    border-radius: var(--r-md);
    border: 2px solid transparent;
    background: var(--bg-3);
    cursor: pointer;
    overflow: hidden;
    opacity: 0.72;
    transition: opacity var(--t-1) var(--ease), transform var(--t-2) var(--ease), border-color var(--t-1);
  }
  .thumb:hover { opacity: 1; transform: translateY(-2px); }
  .thumb.active { opacity: 1; border-color: var(--accent-hi); box-shadow: var(--glow); }
  img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .badge, .fav { position: absolute; display: grid; place-items: center; border-radius: 6px; background: rgba(0, 0, 0, 0.55); color: white; }
  .badge { right: 4px; bottom: 4px; width: 18px; height: 18px; }
  .fav { left: 4px; top: 4px; width: 16px; height: 16px; color: var(--warn); }
  .badge :global(svg), .fav :global(svg) { width: 10px; height: 10px; fill: currentColor; }
</style>
