<script lang="ts">
  interface Props {
    value: number;
    min: number;
    max: number;
    step?: number;
    label?: string;
    unit?: string;
    disabled?: boolean;
    format?: (v: number) => string;
    onchange?: (v: number) => void;
  }
  let { value = $bindable(), min, max, step = 1, label = '', unit = '', disabled = false, format, onchange }: Props = $props();
  const pct = $derived(((Number(value) - min) / (max - min || 1)) * 100);
  let editing = $state(false);
  let draft = $state('');

  function commit() {
    editing = false;
    const n = Number(draft);
    if (!Number.isNaN(n)) {
      const snapped = Math.round(Math.min(max, Math.max(min, n)) / step) * step;
      value = Number(snapped.toFixed(4));
      onchange?.(value);
    }
  }
  const shown = $derived(format ? format(Number(value)) : `${Number(value)}${unit}`);
</script>

<div class="slider" class:disabled>
  {#if label}
    <div class="top">
      <span class="label">{label}</span>
      {#if editing}
        <!-- svelte-ignore a11y_autofocus -->
        <input class="num" autofocus bind:value={draft} onblur={commit} onkeydown={(e) => e.key === 'Enter' && commit()} />
      {:else}
        <button type="button" class="val tnum" {disabled} onclick={() => { draft = String(value); editing = true; }}>{shown}</button>
      {/if}
    </div>
  {/if}
  <input type="range" {min} {max} {step} bind:value {disabled} style="--p:{pct}%" oninput={() => onchange?.(Number(value))} />
</div>

<style>
  .slider { display: flex; flex-direction: column; gap: 6px; }
  .disabled { opacity: 0.45; }
  .top { display: flex; justify-content: space-between; align-items: center; height: 20px; }
  .label { font-size: var(--fs-sm); color: var(--text-1); font-weight: 550; }
  .val { background: none; border: 0; color: var(--text-2); font-size: var(--fs-sm); cursor: text; padding: 0 2px; border-radius: 4px; }
  .val:hover { color: var(--text-0); background: rgba(255, 255, 255, 0.05); }
  .num { width: 70px; text-align: right; background: var(--bg-1); border: 1px solid var(--select-line); border-radius: 5px; font-size: var(--fs-sm); padding: 0 4px; outline: none; }
  input[type='range'] {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 18px;
    background: transparent;
    cursor: pointer;
    margin: 0;
  }
  input[type='range']::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: 4px;
    background: linear-gradient(90deg, var(--accent-hi) 0, var(--accent) var(--p), rgba(255, 255, 255, 0.09) var(--p));
  }
  input[type='range']::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 14px;
    height: 14px;
    margin-top: -5px;
    border-radius: 50%;
    background: var(--text-0);
    border: 0;
    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.35), 0 2px 6px rgba(0, 0, 0, 0.5);
    transition: transform var(--t-1) var(--ease), box-shadow var(--t-1);
  }
  input[type='range']:hover::-webkit-slider-thumb { transform: scale(1.12); box-shadow: 0 0 0 5px rgba(139, 92, 246, 0.3), 0 2px 6px rgba(0, 0, 0, 0.5); }
  input[type='range']::-moz-range-track { height: 4px; border-radius: 4px; background: rgba(255, 255, 255, 0.09); }
  input[type='range']::-moz-range-progress { height: 4px; border-radius: 4px; background: var(--accent); }
  input[type='range']::-moz-range-thumb { width: 14px; height: 14px; border: 0; border-radius: 50%; background: var(--text-0); }
</style>
