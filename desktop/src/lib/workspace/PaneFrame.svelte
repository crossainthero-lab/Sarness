<script lang="ts">
  import { Code2, GripVertical, Image, Clapperboard, Maximize2, Minimize2, MessagesSquare, Minus, X } from '@lucide/svelte';
  import { ws, closePane, focusPane, setKind, swapPanes, toggleMaximize, toggleMinimize, type Pane, type PaneKind } from '../stores/panes.svelte';
  import { activeJobs } from '../stores/jobs.svelte';
  import Chat from '../views/Chat.svelte';
  import Images from '../views/Images.svelte';
  import Videos from '../views/Videos.svelte';
  import IconButton from '../ui/IconButton.svelte';
  import Menu, { type MenuItem } from '../ui/Menu.svelte';

  let { pane, visible, area, index }: { pane: Pane; visible: boolean; area: string; index: number } = $props();

  const KINDS: { kind: PaneKind; label: string; icon: any }[] = [
    { kind: 'chat', label: 'Chat', icon: MessagesSquare },
    { kind: 'code', label: 'Code', icon: Code2 },
    { kind: 'image', label: 'Image', icon: Image },
    { kind: 'video', label: 'Video', icon: Clapperboard },
  ];
  const meta = $derived(KINDS.find((k) => k.kind === pane.kind)!);
  const focused = $derived(ws.focus === pane.id);
  const maximized = $derived(ws.maximized === pane.id);
  const canClose = $derived(ws.panes.length > 1);
  const canMinimize = $derived(ws.panes.length - ws.minimized.length > 1);
  // Live work in the engine queue for this pane's kind (image/video only).
  const busy = $derived(pane.kind === 'image' || pane.kind === 'video' ? activeJobs(pane.kind).length : 0);

  let menu = $state({ open: false, x: 0, y: 0, items: [] as MenuItem[] });
  let dropTarget = $state(false);

  function kindMenu(e: MouseEvent) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    menu = { open: true, x: r.left, y: r.bottom + 4, items: KINDS.map((k) => ({ label: k.label, icon: k.icon, run: () => setKind(pane.id, k.kind) })) };
  }

  function dragStart(e: DragEvent) {
    e.dataTransfer?.setData('application/x-sarness-pane', pane.id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
  }
  function over(e: DragEvent) {
    if (e.dataTransfer?.types.includes('application/x-sarness-pane')) {
      e.preventDefault();
      dropTarget = true;
    }
  }
  function drop(e: DragEvent) {
    dropTarget = false;
    const from = e.dataTransfer?.getData('application/x-sarness-pane');
    if (from) {
      e.preventDefault();
      swapPanes(from, pane.id);
    }
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_click_events_have_key_events -->
<section class="pane" class:focused class:drop={dropTarget} class:hidden={!visible} style="grid-area:{area}"
  aria-label="{meta.label} session {index + 1}"
  onpointerdown={() => focusPane(pane.id)} onfocusin={() => focusPane(pane.id)}
  ondragover={over} ondragleave={() => (dropTarget = false)} ondrop={drop}>
  <header>
    <span class="grip" draggable="true" ondragstart={dragStart} title="Drag onto another session to swap places" role="presentation"><GripVertical /></span>
    <button class="kind" onclick={kindMenu} title="Change session type"><meta.icon />{meta.label}<span class="num">{index + 1}</span></button>
    {#if busy}<span class="busy" title="{busy} {pane.kind} job{busy === 1 ? '' : 's'} on the server">{busy}</span>{/if}
    <span class="sp"></span>
    <IconButton label="Minimise session" size="sm" disabled={!canMinimize} onclick={() => toggleMinimize(pane.id)}><Minus /></IconButton>
    <IconButton label={maximized ? 'Restore layout' : 'Maximise session'} size="sm" onclick={() => toggleMaximize(pane.id)}>{#if maximized}<Minimize2 />{:else}<Maximize2 />{/if}</IconButton>
    <IconButton label="Close session" size="sm" disabled={!canClose} onclick={() => closePane(pane.id)}><X /></IconButton>
  </header>
  <div class="body">
    {#if pane.kind === 'chat'}<Chat paneId={pane.id} variant="chat" active={visible} />
    {:else if pane.kind === 'code'}<Chat paneId={pane.id} variant="code" active={visible} />
    {:else if pane.kind === 'image'}<Images paneId={pane.id} active={visible} />
    {:else}<Videos paneId={pane.id} active={visible} />{/if}
  </div>
</section>

<Menu bind:open={menu.open} bind:x={menu.x} bind:y={menu.y} bind:items={menu.items} />

<style>
  .pane { position: relative; display: flex; flex-direction: column; min-width: 0; min-height: 0; background: var(--bg-0); border: 1px solid var(--line-1); border-radius: var(--r-lg); overflow: hidden; transition: border-color var(--t-1); }
  .pane.focused { border-color: var(--select-line); }
  .pane.drop { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-ghost); }
  .pane.hidden { display: none; }
  header { display: flex; align-items: center; gap: 4px; height: 36px; padding: 0 6px 0 2px; background: var(--bg-1); border-bottom: 1px solid var(--line-0); flex-shrink: 0; }
  .grip { display: grid; place-items: center; width: 20px; height: 28px; color: var(--text-3); cursor: grab; }
  .grip :global(svg) { width: 14px; height: 14px; }
  .kind { display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 8px; border: 0; border-radius: var(--r-sm); background: none; color: var(--text-0); font-weight: 600; font-size: var(--fs-sm); cursor: pointer; }
  .kind:hover { background: rgba(var(--fg-rgb), 0.06); }
  .kind :global(svg) { width: 14px; height: 14px; color: var(--accent); }
  .num { color: var(--text-3); font-weight: 500; font-size: var(--fs-xs); }
  .busy { min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px; background: var(--accent); color: var(--text-inv); font-size: 11px; font-weight: 700; display: grid; place-items: center; animation: pulse-ring 1.8s infinite; }
  .sp { flex: 1; }
  .body { flex: 1; min-height: 0; position: relative; }
  .body > :global(*) { height: 100%; }
</style>
