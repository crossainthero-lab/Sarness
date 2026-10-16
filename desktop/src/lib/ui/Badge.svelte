<script lang="ts">
  import type { Snippet } from 'svelte';
  let { tone = 'neutral', children, dot = false }: { tone?: 'neutral' | 'accent' | 'ok' | 'warn' | 'err' | 'info'; children?: Snippet; dot?: boolean } = $props();
</script>

<span class="badge {tone}">{#if dot}<i></i>{/if}{@render children?.()}</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    height: 20px;
    padding: 0 7px;
    border-radius: var(--r-full);
    font-size: var(--fs-xs);
    font-weight: 600;
    letter-spacing: 0.01em;
    white-space: nowrap;
    background: rgba(var(--fg-rgb), 0.06);
    color: var(--text-1);
  }
  i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
  .accent { background: var(--accent-ghost); color: var(--lavender); }
  .ok { background: var(--ok-bg); color: var(--ok); }
  .warn { background: var(--warn-bg); color: var(--warn); }
  .err { background: var(--err-bg); color: var(--err); }
  .info { background: var(--info-bg); color: var(--info); }
</style>
