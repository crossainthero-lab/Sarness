<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  import Spinner from './Spinner.svelte';

  interface Props extends HTMLButtonAttributes {
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle';
    size?: 'sm' | 'md' | 'lg';
    loading?: boolean;
    block?: boolean;
    children?: Snippet;
  }
  let { variant = 'secondary', size = 'md', loading = false, block = false, children, disabled, class: cls = '', ...rest }: Props = $props();
</script>

<button class="btn {variant} {size} {cls}" class:block disabled={disabled || loading} aria-busy={loading} {...rest}>
  {#if loading}<Spinner size={size === 'lg' ? 16 : 14} />{/if}
  {@render children?.()}
</button>

<style>
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    height: 32px;
    padding: 0 13px;
    border-radius: var(--r-md);
    border: 1px solid transparent;
    font-weight: 550;
    font-size: var(--fs-md);
    letter-spacing: -0.005em;
    cursor: pointer;
    white-space: nowrap;
    transition: background var(--t-1) var(--ease), border-color var(--t-1) var(--ease), color var(--t-1) var(--ease),
      transform var(--t-1) var(--ease), box-shadow var(--t-2) var(--ease), opacity var(--t-1);
  }
  .btn:active:not(:disabled) { transform: translateY(0.5px) scale(0.985); }
  .btn:disabled { opacity: 0.45; cursor: default; }
  .btn :global(svg) { width: 15px; height: 15px; flex-shrink: 0; }
  .sm { height: 26px; padding: 0 9px; font-size: var(--fs-sm); border-radius: var(--r-sm); gap: 5px; }
  .sm :global(svg) { width: 13px; height: 13px; }
  .lg { height: 40px; padding: 0 18px; font-size: var(--fs-lg); border-radius: var(--r-lg); }
  .block { width: 100%; }

  .primary {
    background: linear-gradient(180deg, #9a6cff, #7c4ff0);
    color: white;
    border-color: rgba(255, 255, 255, 0.08);
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.22) inset, 0 6px 18px rgba(124, 58, 237, 0.28);
  }
  .primary:hover:not(:disabled) {
    background: linear-gradient(180deg, #a57bff, #8657f5);
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.25) inset, 0 8px 24px rgba(124, 58, 237, 0.38);
  }
  .secondary {
    background: var(--bg-4);
    border-color: var(--line-1);
    color: var(--text-0);
    box-shadow: var(--shadow-1);
  }
  .secondary:hover:not(:disabled) { background: var(--bg-5); border-color: var(--line-2); }
  .ghost { background: transparent; color: var(--text-1); }
  .ghost:hover:not(:disabled) { background: rgba(255, 255, 255, 0.05); color: var(--text-0); }
  .subtle { background: var(--accent-ghost); color: var(--lavender); }
  .subtle:hover:not(:disabled) { background: rgba(139, 92, 246, 0.2); }
  .danger { background: var(--err-bg); color: var(--err); border-color: rgba(244, 113, 116, 0.2); }
  .danger:hover:not(:disabled) { background: rgba(244, 113, 116, 0.2); }
</style>
