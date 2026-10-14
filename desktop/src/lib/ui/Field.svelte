<script lang="ts">
  import type { Snippet } from 'svelte';
  let { label, hint = '', error = '', children, aside }: { label?: string; hint?: string; error?: string; children: Snippet; aside?: Snippet } = $props();
</script>

<div class="field">
  {#if label || aside}
    <div class="head">
      {#if label}<span class="label">{label}</span>{/if}
      {#if aside}<span class="aside">{@render aside()}</span>{/if}
    </div>
  {/if}
  {@render children()}
  {#if error}<p class="error">{error}</p>{:else if hint}<p class="hint">{hint}</p>{/if}
</div>

<style>
  .field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .label { font-size: var(--fs-sm); font-weight: 550; color: var(--text-1); }
  .aside { font-size: var(--fs-sm); color: var(--text-2); }
  .hint { font-size: var(--fs-xs); color: var(--text-3); line-height: 1.45; }
  .error { font-size: var(--fs-xs); color: var(--err); }
</style>
