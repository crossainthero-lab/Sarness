<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements';
  import type { Snippet } from 'svelte';
  interface Props extends Omit<HTMLInputAttributes, 'size'> {
    value?: string | number | null;
    mono?: boolean;
    icon?: Snippet;
    size?: 'sm' | 'md';
  }
  let { value = $bindable(''), mono = false, icon, size = 'md', class: cls = '', ...rest }: Props = $props();
</script>

<label class="input {size} {cls}" class:mono class:has-icon={!!icon}>
  {#if icon}<span class="icon">{@render icon()}</span>{/if}
  <input bind:value spellcheck="false" autocomplete="off" {...rest} />
</label>

<style>
  .input {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 34px;
    padding: 0 11px;
    border-radius: var(--r-md);
    background: var(--bg-1);
    border: 1px solid var(--line-1);
    transition: border-color var(--t-1) var(--ease), box-shadow var(--t-2) var(--ease), background var(--t-1);
    min-width: 0;
  }
  .sm { height: 28px; padding: 0 9px; border-radius: var(--r-sm); }
  .input:hover { border-color: var(--line-2); }
  .input:focus-within { border-color: var(--select-line); box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.14); background: var(--bg-0); }
  input {
    flex: 1;
    min-width: 0;
    background: none;
    border: 0;
    outline: none;
    height: 100%;
    font-size: var(--fs-md);
    color: var(--text-0);
  }
  input::placeholder { color: var(--text-3); }
  .mono input { font-family: var(--font-mono); font-size: var(--fs-sm); }
  .icon { display: grid; place-items: center; color: var(--text-3); }
  .icon :global(svg) { width: 15px; height: 15px; }
  input[type='number']::-webkit-inner-spin-button { opacity: 0.4; }
</style>
