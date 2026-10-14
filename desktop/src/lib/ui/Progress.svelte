<script lang="ts">
  /** Real progress only: pass null for an indeterminate (unknown) state. */
  let { value = null, height = 4, tone = 'accent' }: { value?: number | null; height?: number; tone?: 'accent' | 'ok' | 'warn' | 'err' } = $props();
</script>

<div class="track {tone}" style="height:{height}px" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={value === null ? undefined : Math.round(value * 100)}>
  {#if value === null}
    <div class="indet"></div>
  {:else}
    <div class="fill" style="transform:scaleX({Math.max(0, Math.min(1, value))})"></div>
  {/if}
</div>

<style>
  .track {
    position: relative;
    width: 100%;
    overflow: hidden;
    border-radius: var(--r-full);
    background: rgba(255, 255, 255, 0.06);
  }
  .fill {
    position: absolute;
    inset: 0;
    transform-origin: left;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--accent-lo), var(--accent-hi));
    transition: transform 260ms var(--ease-out);
  }
  .ok .fill { background: var(--ok); }
  .warn .fill { background: var(--warn); }
  .err .fill { background: var(--err); }
  .indet {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 35%;
    border-radius: inherit;
    background: linear-gradient(90deg, transparent, var(--accent-hi), transparent);
    animation: slide 1.3s var(--ease) infinite;
  }
  @keyframes slide {
    from { transform: translateX(-100%); }
    to { transform: translateX(300%); }
  }
</style>
