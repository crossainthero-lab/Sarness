<script lang="ts">
  import { Search, Cpu } from '@lucide/svelte';
  import { tick } from 'svelte';
  import type { NodeLibrary, NodeSpec } from '../api/types';
  import { compatible, inputSockets } from './graph';

  interface Props {
    lib: NodeLibrary;
    x: number;
    y: number;
    /** When set, only nodes with an input accepting this type are shown. */
    acceptType?: string | null;
    onpick: (spec: NodeSpec) => void;
    onclose: () => void;
  }
  let { lib, x, y, acceptType = null, onpick, onclose }: Props = $props();
  let q = $state('');
  let active = $state(0);
  let input: HTMLInputElement | undefined = $state();
  let listEl: HTMLDivElement | undefined = $state();

  const order = $derived(lib.categories);
  const results = $derived.by(() => {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    let list = lib.nodes.filter((n) => !n.type.startsWith('test.'));
    if (acceptType) list = list.filter((n) => inputSockets(n).some((s) => compatible(acceptType!, s.type)));
    if (terms.length) {
      list = list.filter((n) => {
        const hay = `${n.title} ${n.category} ${n.type} ${n.description}`.toLowerCase();
        return terms.every((t) => hay.includes(t));
      });
    }
    return list.sort((a, b) => {
      const ca = order.indexOf(a.category), cb = order.indexOf(b.category);
      return (ca < 0 ? 99 : ca) - (cb < 0 ? 99 : cb) || a.title.localeCompare(b.title);
    });
  });

  $effect(() => {
    void q;
    active = 0;
  });
  tick().then(() => input?.focus());

  function key(e: KeyboardEvent) {
    if (e.key === 'Escape') { onclose(); e.preventDefault(); }
    else if (e.key === 'ArrowDown') { active = Math.min(results.length - 1, active + 1); e.preventDefault(); scroll(); }
    else if (e.key === 'ArrowUp') { active = Math.max(0, active - 1); e.preventDefault(); scroll(); }
    else if (e.key === 'Enter' && results[active]) { onpick(results[active]); e.preventDefault(); }
  }
  function scroll() {
    tick().then(() => listEl?.querySelector(`[data-i="${active}"]`)?.scrollIntoView({ block: 'nearest' }));
  }
  const left = $derived(Math.min(x, window.innerWidth - 400));
  const top = $derived(Math.min(y, window.innerHeight - 460));
</script>

<svelte:window onmousedown={(e) => !(e.target as HTMLElement).closest('.palette') && onclose()} />

<div class="palette glass" style="left:{left}px;top:{top}px" role="dialog" aria-label="Add node">
  <div class="search">
    <Search />
    <input bind:this={input} bind:value={q} placeholder={acceptType ? `Nodes accepting ${acceptType}…` : 'Search nodes…'} onkeydown={key} spellcheck="false" />
  </div>
  <div class="list" bind:this={listEl}>
    {#each results as n, i (n.type)}
      {#if i === 0 || results[i - 1].category !== n.category}<div class="cat">{n.category}</div>{/if}
      <button class="item" class:active={i === active} data-i={i} onmouseenter={() => (active = i)} onclick={() => onpick(n)}>
        <span class="t">{n.title}{#if n.gpu}<Cpu />{/if}</span>
        <span class="d">{n.description}</span>
        <span class="sig">{n.inputs.map((s) => s.type).join(', ') || '—'} → {n.outputs.map((s) => s.type).join(', ') || (n.output_node ? 'saved' : '—')}</span>
      </button>
    {/each}
    {#if !results.length}<p class="none">No matching nodes</p>{/if}
  </div>
</div>

<style>
  .palette {
    position: fixed;
    z-index: 9200;
    width: 380px;
    max-height: 450px;
    display: flex;
    flex-direction: column;
    border-radius: var(--r-lg);
    background: var(--glass-strong);
    box-shadow: var(--shadow-3);
    animation: pop-in var(--t-2) var(--ease-out);
    overflow: hidden;
  }
  .search { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid var(--line-1); }
  .search :global(svg) { width: 15px; height: 15px; color: var(--text-3); }
  .search input { flex: 1; background: none; border: 0; outline: none; font-size: var(--fs-md); color: var(--text-0); }
  .list { overflow-y: auto; padding: 4px; }
  .cat { padding: 8px 8px 3px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-3); }
  .item { display: flex; flex-direction: column; gap: 1px; width: 100%; padding: 7px 9px; border: 0; border-radius: var(--r-sm); background: none; text-align: left; cursor: pointer; color: var(--text-1); }
  .item.active { background: var(--select-bg); }
  .t { display: flex; align-items: center; gap: 6px; font-weight: 600; color: var(--text-0); font-size: var(--fs-sm); }
  .t :global(svg) { width: 11px; height: 11px; color: var(--text-3); }
  .d { font-size: 11px; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .sig { font-size: 10px; color: var(--text-3); font-family: var(--font-mono); }
  .none { padding: 14px; color: var(--text-3); font-size: var(--fs-sm); }
</style>
