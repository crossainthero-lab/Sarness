<script lang="ts">
  import { CircleCheck, CircleAlert, Info, TriangleAlert, X } from '@lucide/svelte';
  import { dismiss, toasts } from '../stores/toast.svelte';
  const icons = { success: CircleCheck, error: CircleAlert, warning: TriangleAlert, info: Info };
</script>

<div class="toaster" aria-live="polite">
  {#each toasts as t (t.id)}
    {@const Icon = icons[t.kind]}
    <div class="toast {t.kind}">
      <Icon />
      <div class="txt">
        <strong>{t.title}</strong>
        {#if t.body}<p class="selectable">{t.body}</p>{/if}
      </div>
      {#if t.action}
        <button class="act" onclick={() => { t.action?.run(); dismiss(t.id); }}>{t.action.label}</button>
      {/if}
      <button class="x" aria-label="Dismiss" onclick={() => dismiss(t.id)}><X /></button>
    </div>
  {/each}
</div>

<style>
  .toaster {
    position: fixed;
    right: 18px;
    bottom: calc(var(--statusbar-h) + 14px);
    z-index: 9800;
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: min(380px, calc(100vw - 36px));
    pointer-events: none;
  }
  .toast {
    pointer-events: auto;
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 11px 10px 11px 13px;
    border-radius: var(--r-lg);
    background: var(--glass-strong);
    backdrop-filter: blur(16px);
    border: 1px solid var(--line-1);
    box-shadow: var(--shadow-3);
    animation: rise-in var(--t-3) var(--ease-out);
  }
  .toast > :global(svg) { width: 17px; height: 17px; margin-top: 1px; flex-shrink: 0; }
  .success > :global(svg) { color: var(--ok); }
  .error > :global(svg) { color: var(--err); }
  .warning > :global(svg) { color: var(--warn); }
  .info > :global(svg) { color: var(--lavender); }
  .txt { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  strong { font-weight: 600; font-size: var(--fs-md); }
  p { font-size: var(--fs-sm); color: var(--text-2); overflow-wrap: anywhere; max-height: 120px; overflow: auto; }
  .act { border: 0; background: var(--accent-ghost); color: var(--lavender); border-radius: var(--r-sm); padding: 4px 9px; font-size: var(--fs-sm); font-weight: 600; cursor: pointer; }
  .x { border: 0; background: none; color: var(--text-3); cursor: pointer; padding: 2px; border-radius: 5px; display: grid; }
  .x:hover { color: var(--text-0); background: rgba(var(--fg-rgb), 0.06); }
  .x :global(svg) { width: 14px; height: 14px; }
</style>
