<script lang="ts">
  import { Plus, Workflow as WorkflowIcon, SlidersHorizontal } from '@lucide/svelte';
  import type { Snippet } from 'svelte';
  import type { Generation, Job } from '../api/types';
  import type { History } from '../stores/history.svelte';
  import { activeJobs } from '../stores/jobs.svelte';
  import { currentProject, folderPath, currentFolder } from '../stores/projects.svelte';
  import Splitter from '../ui/Splitter.svelte';
  import Segmented from '../ui/Segmented.svelte';
  import Button from '../ui/Button.svelte';
  import OutputViewer from './OutputViewer.svelte';
  import HistoryStrip from './HistoryStrip.svelte';
  import ActionBar from './ActionBar.svelte';

  interface Props {
    kind: 'image' | 'video';
    paneId: string;
    title: string;
    mode: 'simple' | 'advanced';
    history: History;
    active: boolean;
    controls: Snippet;
    advanced: Snippet;
    empty: Snippet;
    onmode: (m: 'simple' | 'advanced') => void;
    onnew: () => void;
    onrerun: (g: Generation, exact: boolean) => void;
    onvary?: (g: Generation, strength: number) => void;
    onedit: (g: Generation) => void;
  }
  let { kind, paneId, title, mode, history, active, controls, advanced, empty, onmode, onnew, onrerun, onvary, onedit }: Props = $props();
  let panel = $state(372);

  // Only this pane's own jobs: other panes' work shows in their panes.
  const mine = $derived(activeJobs(kind).filter((j) => history.state.follow.has(j.id)));
  let rootEl: HTMLDivElement | undefined = $state();
  let width = $state(900);
  const narrow = $derived(width < 760);
  let controlsOpen = $state(true);
  const running: Job | null = $derived(mine.find((j) => j.status === 'running') ?? mine[0] ?? null);
  const queued = $derived(Math.max(0, mine.length - (running ? 1 : 0)));
  const current = $derived(history.current);
  const dest = $derived(folderPath(currentProject(), currentFolder()?.id ?? null));

  $effect(() => {
    if (active && !history.state.loaded && !history.state.loading) history.load().catch(() => {});
  });

  function keys(e: KeyboardEvent) {
    if (!active || mode !== 'simple' || !rootEl?.matches(':focus-within')) return;
    if ((e.target as HTMLElement)?.closest('input, textarea, [contenteditable], select')) return;
    if (e.key === 'ArrowLeft') { history.prev(); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { history.next(); e.preventDefault(); }
  }
</script>

<svelte:window onkeydown={keys} />

<div class="studio" bind:clientWidth={width} bind:this={rootEl}>
  <header>
    <span class="dest" title="New generations are saved here">{dest}</span>
    <div class="spacer"></div>
    {#if mode === 'simple'}
      {#if narrow}
        <Button size="sm" variant="ghost" onclick={() => (controlsOpen = !controlsOpen)}><SlidersHorizontal />{controlsOpen ? 'Hide settings' : 'Settings'}</Button>
      {/if}
      <Button size="sm" variant="ghost" onclick={onnew}><Plus />New</Button>
    {/if}
    <Segmented value={mode} items={[{ value: 'simple', label: 'Simple', icon: SlidersHorizontal }, { value: 'advanced', label: 'Advanced', icon: WorkflowIcon }]} onchange={(m) => onmode(m)} />
  </header>

  {#if mode === 'simple'}
    <div class="body" class:stack={narrow}>
      {#if !narrow}
        <aside class="controls" style="width:{panel}px">{@render controls()}</aside>
        <Splitter id="{paneId}-controls" bind:size={panel} min={300} max={560} />
      {:else if controlsOpen}
        <aside class="controls drawer">{@render controls()}</aside>
      {/if}
      <section class="out">
        <OutputViewer {current} {running} {queued} {kind}
          canPrev={history.state.index < history.state.items.length - 1} canNext={history.state.index > 0}
          onprev={() => history.prev()} onnext={() => history.next()} {empty} />
        {#if current}
          <ActionBar g={current} onrerun={(exact) => onrerun(current, exact)} onvary={onvary ? (s) => onvary(current, s) : undefined} onedit={() => onedit(current)} />
        {/if}
        {#if history.state.items.length}<HistoryStrip {history} />{/if}
      </section>
    </div>
  {:else}
    <div class="adv">{@render advanced()}</div>
  {/if}
</div>

<style>
  .studio { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  header { display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 10px 0 14px; border-bottom: 1px solid var(--line-0); flex-shrink: 0; }
  .dest { font-size: var(--fs-xs); color: var(--text-3); padding: 3px 8px; border-radius: var(--r-full); background: rgba(var(--fg-rgb), 0.04); max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .spacer { flex: 1; }
  .body { flex: 1; display: flex; min-height: 0; }
  .body.stack { flex-direction: column; }
  .controls.drawer { width: auto; max-height: 52%; border-bottom: 1px solid var(--line-1); }
  .controls { flex-shrink: 0; overflow-y: auto; overflow-x: hidden; background: var(--bg-1); }
  .out { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
  .adv { flex: 1; min-height: 0; display: flex; }
</style>
