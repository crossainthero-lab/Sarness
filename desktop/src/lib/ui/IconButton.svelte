<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  import { tooltip } from './tooltip';

  interface Props extends HTMLButtonAttributes {
    label: string;
    size?: 'sm' | 'md' | 'lg';
    active?: boolean;
    tone?: 'default' | 'danger' | 'accent';
    tip?: boolean;
    children?: Snippet;
  }
  let { label, size = 'md', active = false, tone = 'default', tip = true, children, class: cls = '', ...rest }: Props = $props();
</script>

<button class="ib {size} {tone} {cls}" class:active aria-label={label} use:tooltip={tip ? label : null} {...rest}>
  {@render children?.()}
</button>

<style>
  .ib {
    display: inline-grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: var(--r-md);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-2);
    cursor: pointer;
    flex-shrink: 0;
    transition: background var(--t-1) var(--ease), color var(--t-1) var(--ease), transform var(--t-1) var(--ease);
  }
  .ib :global(svg) { width: 16px; height: 16px; }
  .sm { width: 24px; height: 24px; border-radius: var(--r-sm); }
  .sm :global(svg) { width: 14px; height: 14px; }
  .lg { width: 36px; height: 36px; }
  .lg :global(svg) { width: 18px; height: 18px; }
  .ib:hover:not(:disabled) { background: rgba(var(--fg-rgb), 0.06); color: var(--text-0); }
  .ib:active:not(:disabled) { transform: scale(0.94); }
  .ib:disabled { opacity: 0.35; cursor: default; }
  .active { background: var(--select-bg); color: var(--lavender); }
  .active:hover:not(:disabled) { background: rgba(var(--accent-rgb), 0.2); color: var(--lavender); }
  .danger:hover:not(:disabled) { color: var(--err); background: var(--err-bg); }
  .accent { color: var(--accent-hi); }
</style>
