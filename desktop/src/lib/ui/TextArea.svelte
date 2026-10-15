<script lang="ts">
  import type { HTMLTextareaAttributes } from 'svelte/elements';
  interface Props extends HTMLTextareaAttributes {
    value?: string;
    minRows?: number;
    maxRows?: number;
    mono?: boolean;
    el?: HTMLTextAreaElement | null;
  }
  let { value = $bindable(''), minRows = 2, maxRows = 14, mono = false, el = $bindable(null), class: cls = '', ...rest }: Props = $props();

  function fit() {
    if (!el) return;
    const lh = parseFloat(getComputedStyle(el).lineHeight) || 20;
    const pad = 20;
    el.style.height = 'auto';
    const h = Math.min(Math.max(el.scrollHeight, minRows * lh + pad), maxRows * lh + pad);
    el.style.height = `${h}px`;
    el.style.overflowY = el.scrollHeight > h ? 'auto' : 'hidden';
  }
  $effect(() => {
    void value;
    fit();
  });
</script>

<textarea bind:this={el} bind:value class="ta {cls}" class:mono oninput={fit} spellcheck="true" {...rest}></textarea>

<style>
  .ta {
    width: 100%;
    resize: none;
    padding: 10px 12px;
    border-radius: var(--r-md);
    background: var(--bg-1);
    border: 1px solid var(--line-1);
    color: var(--text-0);
    font-size: var(--fs-md);
    line-height: 1.55;
    outline: none;
    transition: border-color var(--t-1) var(--ease), box-shadow var(--t-2) var(--ease);
  }
  .ta:hover { border-color: var(--line-2); }
  .ta:focus { border-color: var(--select-line); box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.14); }
  .ta::placeholder { color: var(--text-3); }
  .mono { font-family: var(--font-mono); font-size: var(--fs-sm); }
</style>
