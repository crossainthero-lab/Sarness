<script lang="ts">
  let { checked = $bindable(false), label = '', hint = '', disabled = false, onchange }: { checked?: boolean; label?: string; hint?: string; disabled?: boolean; onchange?: (v: boolean) => void } = $props();
</script>

<label class="toggle" class:disabled>
  <span class="text">
    {#if label}<span class="label">{label}</span>{/if}
    {#if hint}<span class="hint">{hint}</span>{/if}
  </span>
  <input type="checkbox" bind:checked {disabled} onchange={() => onchange?.(checked)} />
  <span class="track" aria-hidden="true"><span class="knob"></span></span>
</label>

<style>
  .toggle { display: flex; align-items: center; gap: 12px; cursor: pointer; justify-content: space-between; }
  .disabled { opacity: 0.45; cursor: default; }
  .text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .label { font-size: var(--fs-md); color: var(--text-0); }
  .hint { font-size: var(--fs-xs); color: var(--text-3); line-height: 1.45; }
  input { position: absolute; opacity: 0; pointer-events: none; }
  .track {
    position: relative;
    width: 34px;
    height: 20px;
    flex-shrink: 0;
    border-radius: 999px;
    background: rgba(var(--fg-rgb), 0.1);
    transition: background var(--t-2) var(--ease);
  }
  .knob {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--text-0);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
    transition: transform var(--t-2) var(--ease);
  }
  input:checked + .track { background: var(--accent); }
  input:checked + .track .knob { transform: translateX(14px); background: var(--text-inv); }
  input:focus-visible + .track { box-shadow: var(--focus); }
</style>
