<script lang="ts">
  import { Code2, Columns2, Grid2x2, Image, Clapperboard, MessagesSquare, PanelLeft, Plus, Rows2, Square } from '@lucide/svelte';
  import { MAX_PANES, addPane, persistWorkspace, setLayout, toggleMinimize, visiblePanes, ws, type PaneKind } from '../stores/panes.svelte';
  import PaneFrame from './PaneFrame.svelte';
  import Menu, { type MenuItem } from '../ui/Menu.svelte';
  import IconButton from '../ui/IconButton.svelte';
  import { tooltip } from '../ui/tooltip';

  const vis = $derived(visiblePanes());
  const n = $derived(vis.length);
  const visIds = $derived(new Set(vis.map((p) => p.id)));
  const minimized = $derived(ws.panes.filter((p) => ws.minimized.includes(p.id)));
  const rows = $derived(ws.orientation === 'rows');

  // Grid areas for the current visible-pane count and orientation.
  const template = $derived.by(() => {
    const c = ws.colRatio;
    const r = ws.rowRatio;
    const cols = `${c}fr ${1 - c}fr`;
    const rws = `${r}fr ${1 - r}fr`;
    if (n <= 1) return { cols: '1fr', rows: '1fr', areas: '"a"' };
    if (n === 2) return rows ? { cols: '1fr', rows: rws, areas: '"a" "b"' } : { cols, rows: '1fr', areas: '"a b"' };
    if (n === 3) return rows ? { cols, rows: rws, areas: '"a a" "b c"' } : { cols, rows: rws, areas: '"a b" "a c"' };
    return { cols, rows: rws, areas: '"a b" "c d"' };
  });
  const names = ['a', 'b', 'c', 'd'];

  // Resize handles as percentage rectangles inside the grid.
  const handles = $derived.by(() => {
    const out: { id: 'col' | 'row'; style: string }[] = [];
    const c = ws.colRatio * 100;
    const r = ws.rowRatio * 100;
    if (n === 2 && !rows) out.push({ id: 'col', style: `left:calc(${c}% - 5px);top:0;bottom:0;width:10px;cursor:col-resize` });
    if (n === 2 && rows) out.push({ id: 'row', style: `top:calc(${r}% - 5px);left:0;right:0;height:10px;cursor:row-resize` });
    if (n === 3 && !rows) {
      out.push({ id: 'col', style: `left:calc(${c}% - 5px);top:0;bottom:0;width:10px;cursor:col-resize` });
      out.push({ id: 'row', style: `top:calc(${r}% - 5px);left:${c}%;right:0;height:10px;cursor:row-resize` });
    }
    if (n === 3 && rows) {
      out.push({ id: 'row', style: `top:calc(${r}% - 5px);left:0;right:0;height:10px;cursor:row-resize` });
      out.push({ id: 'col', style: `left:calc(${c}% - 5px);top:${r}%;bottom:0;width:10px;cursor:col-resize` });
    }
    if (n >= 4) {
      out.push({ id: 'col', style: `left:calc(${c}% - 5px);top:0;bottom:0;width:10px;cursor:col-resize` });
      out.push({ id: 'row', style: `top:calc(${r}% - 5px);left:0;right:0;height:10px;cursor:row-resize` });
    }
    return out;
  });

  let grid: HTMLDivElement | undefined = $state();
  function drag(e: PointerEvent, which: 'col' | 'row') {
    if (!grid) return;
    e.preventDefault();
    const rect = grid.getBoundingClientRect();
    const move = (ev: PointerEvent) => {
      if (which === 'col') ws.colRatio = Math.min(0.8, Math.max(0.2, (ev.clientX - rect.left) / rect.width));
      else ws.rowRatio = Math.min(0.8, Math.max(0.2, (ev.clientY - rect.top) / rect.height));
    };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      persistWorkspace();
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }
  function nudge(e: KeyboardEvent, which: 'col' | 'row') {
    const d = e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -0.03 : e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 0.03 : 0;
    if (!d) return;
    e.preventDefault();
    if (which === 'col') ws.colRatio = Math.min(0.8, Math.max(0.2, ws.colRatio + d));
    else ws.rowRatio = Math.min(0.8, Math.max(0.2, ws.rowRatio + d));
    persistWorkspace();
  }

  let menu = $state({ open: false, x: 0, y: 0, items: [] as MenuItem[] });
  function addMenu(e: MouseEvent) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const kinds: [PaneKind, string, any][] = [['chat', 'Chat', MessagesSquare], ['code', 'Code', Code2], ['image', 'Image', Image], ['video', 'Video', Clapperboard]];
    menu = { open: true, x: r.left, y: r.bottom + 4, items: kinds.map(([k, l, ic]) => ({ label: `New ${l.toLowerCase()} session`, icon: ic, run: () => addPane(k) })) };
  }
  const full = $derived(ws.panes.length >= MAX_PANES);
  const label: Record<PaneKind, string> = { chat: 'Chat', code: 'Code', image: 'Image', video: 'Video' };
</script>

<div class="tiler">
  <div class="bar" role="toolbar" aria-label="Workspace layout">
    <div class="group" role="group" aria-label="Layout">
      <IconButton label="One session" size="sm" onclick={() => setLayout(1)}><Square /></IconButton>
      <IconButton label="Two side by side" size="sm" onclick={() => setLayout(2, 'cols')}><Columns2 /></IconButton>
      <IconButton label="Two stacked" size="sm" onclick={() => setLayout(2, 'rows')}><Rows2 /></IconButton>
      <IconButton label="Three sessions" size="sm" onclick={() => setLayout(3)}><PanelLeft /></IconButton>
      <IconButton label="Four sessions (2×2)" size="sm" onclick={() => setLayout(4)}><Grid2x2 /></IconButton>
    </div>
    <button class="add" onclick={addMenu} disabled={full} use:tooltip={full ? 'Four sessions is the maximum' : null}><Plus />New session</button>
    <div class="sp"></div>
    {#each minimized as p (p.id)}
      <button class="chip" onclick={() => toggleMinimize(p.id)} title="Restore this session">{label[p.kind]} · {ws.panes.indexOf(p) + 1}</button>
    {/each}
  </div>

  <div class="stage" bind:this={grid}>
  <div class="grid" style="grid-template-columns:{template.cols};grid-template-rows:{template.rows};grid-template-areas:{template.areas}">
    {#each ws.panes as pane, i (pane.id)}
      {@const vi = vis.findIndex((p) => p.id === pane.id)}
      <PaneFrame {pane} index={i} visible={visIds.has(pane.id)} area={names[Math.max(0, vi)]} />
    {/each}
  </div>
  <div class="hlayer">
    {#each handles as h (h.id)}
      <div class="handle {h.id}" style={h.style} role="separator" tabindex="0" aria-orientation={h.id === 'col' ? 'vertical' : 'horizontal'}
        aria-label={h.id === 'col' ? 'Resize columns' : 'Resize rows'} onpointerdown={(e) => drag(e, h.id)} onkeydown={(e) => nudge(e, h.id)}
        ondblclick={() => { ws.colRatio = 0.5; ws.rowRatio = 0.5; persistWorkspace(); }}></div>
    {/each}
  </div>
  </div>
</div>

<Menu bind:open={menu.open} bind:x={menu.x} bind:y={menu.y} bind:items={menu.items} />

<style>
  .tiler { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .bar { display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 10px; flex-shrink: 0; }
  .group { display: flex; gap: 2px; padding: 2px; border-radius: var(--r-md); background: var(--bg-2); }
  .add { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; border-radius: var(--r-md); border: 1px solid var(--line-1); background: var(--bg-0); color: var(--text-0); font-weight: 550; font-size: var(--fs-sm); cursor: pointer; }
  .add:hover:not(:disabled) { border-color: var(--accent); }
  .add:disabled { opacity: 0.5; cursor: default; }
  .add :global(svg) { width: 14px; height: 14px; }
  .sp { flex: 1; }
  .chip { height: 26px; padding: 0 10px; border-radius: var(--r-full); border: 1px solid var(--select-line); background: var(--select-bg); color: var(--text-0); font-size: var(--fs-xs); font-weight: 600; cursor: pointer; }
  .stage { position: relative; flex: 1; min-height: 0; margin: 0 8px 8px; }
  .grid { position: absolute; inset: 0; display: grid; gap: 8px; }
  .hlayer { position: absolute; inset: 0; pointer-events: none; }
  .handle { position: absolute; z-index: 10; pointer-events: auto; }
  .handle::after { content: ''; position: absolute; inset: 3px; border-radius: 4px; background: transparent; transition: background var(--t-1); }
  .handle:hover::after, .handle:focus-visible::after { background: var(--accent); opacity: 0.55; }
</style>
