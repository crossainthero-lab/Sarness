<script lang="ts">
  import { X } from '@lucide/svelte';
  import type { Snippet } from 'svelte';
  import IconButton from './IconButton.svelte';

  interface Props {
    open: boolean;
    title?: string;
    subtitle?: string;
    width?: number;
    onclose?: () => void;
    children: Snippet;
    footer?: Snippet;
    dismissible?: boolean;
  }
  let { open = $bindable(), title = '', subtitle = '', width = 520, onclose, children, footer, dismissible = true }: Props = $props();

  function close() {
    if (!dismissible) return;
    open = false;
    onclose?.();
  }
</script>

<svelte:window onkeydown={(e) => open && e.key === 'Escape' && close()} />

{#if open}
  <div class="scrim" role="presentation" onmousedown={(e) => e.target === e.currentTarget && close()}>
    <div class="modal" role="dialog" aria-modal="true" aria-label={title} style="width:min({width}px, calc(100vw - 48px))">
      {#if title}
        <header>
          <div class="titles">
            <h3>{title}</h3>
            {#if subtitle}<p class="muted">{subtitle}</p>{/if}
          </div>
          {#if dismissible}<IconButton label="Close" onclick={close}><X /></IconButton>{/if}
        </header>
      {/if}
      <div class="body">{@render children()}</div>
      {#if footer}<footer>{@render footer()}</footer>{/if}
    </div>
  </div>
{/if}

<style>
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 8000;
    display: grid;
    place-items: center;
    background: var(--scrim);
    backdrop-filter: blur(6px);
    animation: fade-in var(--t-2) var(--ease);
  }
  .modal {
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    border-radius: var(--r-xl);
    background: var(--bg-2);
    border: 1px solid var(--line-1);
    box-shadow: var(--shadow-3);
    animation: pop-in var(--t-3) var(--ease-out);
    overflow: hidden;
  }
  header { display: flex; align-items: flex-start; gap: 12px; padding: 18px 18px 6px 22px; }
  .titles { flex: 1; display: flex; flex-direction: column; gap: 3px; }
  .titles p { font-size: var(--fs-sm); }
  .body { padding: 12px 22px 18px; overflow-y: auto; }
  footer { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 18px; border-top: 1px solid var(--line-0); background: var(--bg-1); }
</style>
