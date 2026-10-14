<script lang="ts" module>
  export interface Option<V> {
    value: V;
    label: string;
    hint?: string;
    group?: string;
    disabled?: boolean;
    badge?: string;
  }
</script>

<script lang="ts" generics="T extends string | number | null">
  import { ChevronDown, Check } from '@lucide/svelte';
  import { tick } from 'svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    value: T;
    options: Option<T>[];
    placeholder?: string;
    size?: 'sm' | 'md';
    disabled?: boolean;
    onchange?: (v: T) => void;
    width?: string;
    footer?: Snippet;
  }
  let { value = $bindable(), options, placeholder = 'Select…', size = 'md', disabled = false, onchange, width = '', footer }: Props = $props();

  let open = $state(false);
  let btn: HTMLButtonElement;
  let list: HTMLDivElement | undefined = $state();
  let active = $state(0);
  let pos = $state({ top: 0, left: 0, width: 0, up: false });

  const selected = $derived(options.find((o) => o.value === value));

  async function toggle() {
    if (disabled) return;
    open = !open;
    if (open) {
      const r = btn.getBoundingClientRect();
      const spaceBelow = window.innerHeight - r.bottom;
      pos = { top: r.bottom + 4, left: r.left, width: Math.max(r.width, 220), up: spaceBelow < 280 && r.top > spaceBelow };
      if (pos.up) pos.top = r.top - 4;
      active = Math.max(0, options.findIndex((o) => o.value === value));
      await tick();
      list?.querySelector<HTMLElement>(`[data-i="${active}"]`)?.scrollIntoView({ block: 'nearest' });
    }
  }

  function choose(o: Option<T>) {
    if (o.disabled) return;
    value = o.value;
    open = false;
    onchange?.(o.value);
    btn?.focus();
  }

  function key(e: KeyboardEvent) {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      toggle();
      return;
    }
    if (!open) return;
    if (e.key === 'Escape') { open = false; e.preventDefault(); }
    else if (e.key === 'ArrowDown') { active = Math.min(options.length - 1, active + 1); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { active = Math.max(0, active - 1); e.preventDefault(); }
    else if (e.key === 'Enter') { choose(options[active]); e.preventDefault(); }
    list?.querySelector<HTMLElement>(`[data-i="${active}"]`)?.scrollIntoView({ block: 'nearest' });
  }

  function outside(e: MouseEvent) {
    if (open && !btn.contains(e.target as Node) && !list?.contains(e.target as Node)) open = false;
  }
</script>

<svelte:window onmousedown={outside} onresize={() => (open = false)} />

<button bind:this={btn} type="button" class="select {size}" class:open {disabled} onclick={toggle} onkeydown={key} style:width aria-haspopup="listbox" aria-expanded={open}>
  <span class="value truncate" class:placeholder={!selected}>{selected?.label ?? placeholder}</span>
  {#if selected?.badge}<span class="mini-badge">{selected.badge}</span>{/if}
  <ChevronDown />
</button>

{#if open}
  <div bind:this={list} class="menu glass" role="listbox" style="left:{pos.left}px;{pos.up ? `bottom:${window.innerHeight - pos.top}px` : `top:${pos.top}px`};min-width:{pos.width}px">
    {#each options as o, i (i)}
      {#if o.group && (i === 0 || options[i - 1].group !== o.group)}
        <div class="group">{o.group}</div>
      {/if}
      <button type="button" class="opt" class:active={i === active} class:sel={o.value === value} disabled={o.disabled} data-i={i}
        role="option" aria-selected={o.value === value} onmouseenter={() => (active = i)} onclick={() => choose(o)}>
        <span class="olabel">
          <span class="truncate">{o.label}</span>
          {#if o.hint}<span class="ohint truncate">{o.hint}</span>{/if}
        </span>
        {#if o.badge}<span class="mini-badge">{o.badge}</span>{/if}
        {#if o.value === value}<Check />{/if}
      </button>
    {/each}
    {#if !options.length}<div class="none">Nothing available</div>{/if}
    {#if footer}<div class="foot">{@render footer()}</div>{/if}
  </div>
{/if}

<style>
  .select {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    height: 34px;
    padding: 0 10px 0 11px;
    border-radius: var(--r-md);
    background: var(--bg-1);
    border: 1px solid var(--line-1);
    color: var(--text-0);
    cursor: pointer;
    text-align: left;
    transition: border-color var(--t-1) var(--ease), background var(--t-1);
    min-width: 0;
  }
  .sm { height: 28px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
  .select:hover:not(:disabled) { border-color: var(--line-2); }
  .select.open { border-color: var(--select-line); }
  .select:disabled { opacity: 0.5; cursor: default; }
  .select :global(svg) { width: 14px; height: 14px; color: var(--text-3); flex-shrink: 0; transition: transform var(--t-2) var(--ease); }
  .select.open :global(svg) { transform: rotate(180deg); }
  .value { flex: 1; min-width: 0; }
  .placeholder { color: var(--text-3); }
  .menu {
    position: fixed;
    z-index: 9000;
    max-height: 340px;
    max-width: 440px;
    overflow-y: auto;
    padding: 5px;
    border-radius: var(--r-lg);
    background: var(--glass-strong);
    box-shadow: var(--shadow-3);
    animation: pop-in var(--t-2) var(--ease-out);
  }
  .group { padding: 8px 9px 4px; font-size: var(--fs-xs); color: var(--text-3); font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; }
  .opt {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 7px 9px;
    border: 0;
    border-radius: var(--r-sm);
    background: transparent;
    color: var(--text-1);
    text-align: left;
    cursor: pointer;
  }
  .opt.active { background: rgba(255, 255, 255, 0.06); color: var(--text-0); }
  .opt.sel { color: var(--lavender); }
  .opt:disabled { opacity: 0.4; cursor: default; }
  .opt :global(svg) { width: 14px; height: 14px; color: var(--lavender); flex-shrink: 0; }
  .olabel { display: flex; flex-direction: column; flex: 1; min-width: 0; }
  .ohint { font-size: var(--fs-xs); color: var(--text-3); }
  .mini-badge { font-size: 10px; padding: 1px 6px; border-radius: var(--r-full); background: rgba(255,255,255,0.07); color: var(--text-2); white-space: nowrap; }
  .none { padding: 10px; color: var(--text-3); font-size: var(--fs-sm); }
  .foot { border-top: 1px solid var(--line-1); margin-top: 4px; padding-top: 4px; }
</style>
