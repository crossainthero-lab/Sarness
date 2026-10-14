<script lang="ts">
  import type { ModelCategory } from '../api/types';
  import { byCategory, models } from '../stores/models.svelte';
  import { prefs, persistPrefs } from '../stores/prefs.svelte';
  import Select from '../ui/Select.svelte';
  import { mib } from '../util/format';

  let { value = $bindable(), category, onchange, allowNone = false, noneLabel = 'None', size = 'md' }: {
    value: string | null; category: ModelCategory; onchange?: (v: string | null) => void; allowNone?: boolean; noneLabel?: string; size?: 'sm' | 'md';
  } = $props();

  const options = $derived([
    ...(allowNone ? [{ value: null, label: noneLabel }] : []),
    ...byCategory(category).map((m) => ({
      value: m.id as string | null,
      label: m.name,
      hint: [m.vram_mb ? `~${mib(m.vram_mb)} VRAM` : null, m.family].filter(Boolean).join(' · '),
      badge: m.loaded ? 'loaded' : undefined,
    })),
  ]);
</script>

{#if !allowNone && models.loaded && !byCategory(category).length}
  <button class="none" onclick={() => { prefs.view = 'models'; persistPrefs(); }}>No {category} models installed — open Models to install one</button>
{:else}
  <Select bind:value {options} {size} placeholder="Choose a model" onchange={(v) => onchange?.(v)} />
{/if}

<style>
  .none {
    width: 100%;
    padding: 9px 11px;
    border-radius: var(--r-md);
    border: 1px dashed var(--select-line);
    background: var(--select-bg);
    color: var(--lavender);
    font-size: var(--fs-sm);
    text-align: left;
    cursor: pointer;
  }
</style>
